using System.Net;
using System.Security.Principal;
using Microsoft.Extensions.Hosting.WindowsServices;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddWindowsService(options => options.ServiceName = "EnvPortal Domain Proxy");
builder.Services.AddHostedService<ProxyWorker>();
await builder.Build().RunAsync();

sealed class ProxyWorker : BackgroundService
{
    private readonly ILogger<ProxyWorker> logger;
    private readonly IConfiguration config;
    private readonly HttpClient http;
    private HttpListener? listener;

    public ProxyWorker(ILogger<ProxyWorker> logger, IConfiguration config)
    {
        this.logger = logger;
        this.config = config;
        http = new HttpClient(new HttpClientHandler
        {
            AllowAutoRedirect = false,
            UseCookies = false
        });
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var listenPrefix = config["Proxy:ListenPrefix"] ?? "http://+:8998/";
        listener = new HttpListener
        {
            AuthenticationSchemes = AuthenticationSchemes.IntegratedWindowsAuthentication
        };
        listener.Prefixes.Add(listenPrefix);
        listener.Start();
        logger.LogInformation("EnvPortal domain proxy listening on {ListenPrefix}", listenPrefix);

        while (!stoppingToken.IsCancellationRequested)
        {
            HttpListenerContext context;
            try
            {
                context = await listener.GetContextAsync().WaitAsync(stoppingToken);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Failed to accept request");
                continue;
            }

            _ = Task.Run(() => HandleRequest(context, stoppingToken), stoppingToken);
        }
    }

    public override Task StopAsync(CancellationToken cancellationToken)
    {
        listener?.Stop();
        listener?.Close();
        return base.StopAsync(cancellationToken);
    }

    private async Task HandleRequest(HttpListenerContext context, CancellationToken cancellationToken)
    {
        var identity = context.User?.Identity as WindowsIdentity;
        var rawUser = identity?.Name ?? "";
        if (string.IsNullOrWhiteSpace(rawUser) || !IsAllowed(rawUser))
        {
            context.Response.StatusCode = 403;
            await WriteText(context.Response, "Forbidden", cancellationToken);
            logger.LogWarning("Rejected user {User} from {Remote}", rawUser, context.Request.RemoteEndPoint);
            return;
        }

        var target = BuildTargetUri(context.Request);
        using var request = new HttpRequestMessage(new HttpMethod(context.Request.HttpMethod), target);
        CopyRequestHeaders(context.Request, request);
        AddAuthHeaders(request, rawUser, context.Request.RemoteEndPoint?.Address.ToString() ?? "");

        if (context.Request.HasEntityBody)
        {
            request.Content = new StreamContent(context.Request.InputStream);
            if (!string.IsNullOrWhiteSpace(context.Request.ContentType))
            {
                request.Content.Headers.TryAddWithoutValidation("Content-Type", context.Request.ContentType);
            }
        }

        try
        {
            using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            context.Response.StatusCode = (int)response.StatusCode;
            CopyResponseHeaders(response, context.Response);
            await response.Content.CopyToAsync(context.Response.OutputStream, cancellationToken);
        }
        catch (Exception ex)
        {
            context.Response.StatusCode = 502;
            await WriteText(context.Response, "Bad Gateway", cancellationToken);
            logger.LogError(ex, "Proxy request failed for {Target}", target);
        }
        finally
        {
            context.Response.OutputStream.Close();
        }
    }

    private Uri BuildTargetUri(HttpListenerRequest request)
    {
        var targetBase = new Uri(config["Proxy:TargetBaseUrl"] ?? "http://192.168.20.38:8999/");
        var pathAndQuery = request.RawUrl ?? "/";
        if (pathAndQuery.StartsWith("/", StringComparison.Ordinal)) pathAndQuery = pathAndQuery[1..];
        return new Uri(targetBase, pathAndQuery);
    }

    private bool IsAllowed(string rawUser)
    {
        var allowedFile = config["Proxy:AllowedUsersFile"] ?? "allowed-users.txt";
        var baseDir = AppContext.BaseDirectory;
        var path = Path.IsPathRooted(allowedFile) ? allowedFile : Path.Combine(baseDir, allowedFile);
        if (!File.Exists(path)) return true;
        var normalized = NormalizeUser(rawUser);
        foreach (var line in File.ReadLines(path))
        {
            var item = line.Trim();
            if (item.Length == 0 || item.StartsWith("#", StringComparison.Ordinal)) continue;
            if (NormalizeUser(item) == normalized) return true;
        }
        return false;
    }

    private static string NormalizeUser(string value)
    {
        var text = value.Trim();
        var slash = text.LastIndexOf('\\');
        if (slash >= 0) text = text[(slash + 1)..];
        var at = text.IndexOf('@');
        if (at >= 0) text = text[..at];
        return text.Trim().ToLowerInvariant();
    }

    private void AddAuthHeaders(HttpRequestMessage request, string rawUser, string clientIp)
    {
        var headerName = config["Proxy:HeaderName"] ?? "X-Remote-User";
        request.Headers.Remove(headerName);
        request.Headers.TryAddWithoutValidation(headerName, rawUser);
        request.Headers.Remove("X-Forwarded-User");
        request.Headers.TryAddWithoutValidation("X-Forwarded-User", rawUser);
        request.Headers.Remove("X-Forwarded-For");
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", clientIp);
    }

    private static void CopyRequestHeaders(HttpListenerRequest source, HttpRequestMessage target)
    {
        foreach (var key in source.Headers.AllKeys)
        {
            if (key is null) continue;
            if (string.Equals(key, "Host", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(key, "Authorization", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(key, "Connection", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(key, "Content-Length", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            var values = source.Headers.GetValues(key);
            if (values is not null)
            {
                target.Headers.TryAddWithoutValidation(key, values);
            }
        }
    }

    private static void CopyResponseHeaders(HttpResponseMessage source, HttpListenerResponse target)
    {
        foreach (var header in source.Headers)
        {
            target.Headers[header.Key] = string.Join(",", header.Value);
        }
        foreach (var header in source.Content.Headers)
        {
            if (string.Equals(header.Key, "Content-Length", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            target.Headers[header.Key] = string.Join(",", header.Value);
        }
    }

    private static async Task WriteText(HttpListenerResponse response, string text, CancellationToken cancellationToken)
    {
        var bytes = System.Text.Encoding.UTF8.GetBytes(text);
        response.ContentType = "text/plain; charset=utf-8";
        await response.OutputStream.WriteAsync(bytes, cancellationToken);
        response.OutputStream.Close();
    }
}
