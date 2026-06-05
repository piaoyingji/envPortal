using System.Net;
using System.DirectoryServices;
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
        if (string.Equals(context.Request.HttpMethod, "OPTIONS", StringComparison.OrdinalIgnoreCase))
        {
            ApplyCorsHeaders(context.Request, context.Response);
            context.Response.StatusCode = 204;
            context.Response.OutputStream.Close();
            return;
        }

        var identity = context.User?.Identity as WindowsIdentity;
        var rawUser = identity?.Name ?? "";
        if (string.IsNullOrWhiteSpace(rawUser) || !IsAllowed(rawUser))
        {
            ApplyCorsHeaders(context.Request, context.Response);
            context.Response.StatusCode = 403;
            await WriteText(context.Response, "Forbidden", cancellationToken);
            logger.LogWarning("Rejected user {User} from {Remote}", rawUser, context.Request.RemoteEndPoint);
            return;
        }

        var target = BuildTargetUri(context.Request);
        using var request = new HttpRequestMessage(new HttpMethod(context.Request.HttpMethod), target);
        CopyRequestHeaders(context.Request, request);
        AddAuthHeaders(request, rawUser, context.Request.RemoteEndPoint?.Address.ToString() ?? "", LookupDomainUser(rawUser));

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
            ApplyCorsHeaders(context.Request, context.Response);
            await response.Content.CopyToAsync(context.Response.OutputStream, cancellationToken);
        }
        catch (Exception ex)
        {
            ApplyCorsHeaders(context.Request, context.Response);
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
        var normalized = NormalizeUser(rawUser);
        var deniedFile = config["Proxy:DeniedUsersFile"] ?? "denied-users.txt";
        if (UserFileContains(deniedFile, normalized))
        {
            return false;
        }

        var allowedFile = config["Proxy:AllowedUsersFile"] ?? "";
        if (string.IsNullOrWhiteSpace(allowedFile))
        {
            return true;
        }

        var allowedPath = ResolveLocalPath(allowedFile);
        if (!File.Exists(allowedPath))
        {
            return true;
        }
        return UserFileContains(allowedFile, normalized);
    }

    private static string ResolveLocalPath(string file)
    {
        return Path.IsPathRooted(file) ? file : Path.Combine(AppContext.BaseDirectory, file);
    }

    private static bool UserFileContains(string file, string normalizedUser)
    {
        if (string.IsNullOrWhiteSpace(file)) return false;
        var path = ResolveLocalPath(file);
        if (!File.Exists(path)) return false;
        foreach (var line in File.ReadLines(path))
        {
            var item = line.Trim();
            if (item.Length == 0 || item.StartsWith("#", StringComparison.Ordinal)) continue;
            if (item == "*") return true;
            if (NormalizeUser(item) == normalizedUser) return true;
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

    private DomainUserInfo LookupDomainUser(string rawUser)
    {
        try
        {
            var accountName = NormalizeUser(rawUser);
            using var root = new DirectoryEntry("LDAP://RootDSE");
            var defaultNamingContext = Convert.ToString(root.Properties["defaultNamingContext"].Value) ?? "";
            if (string.IsNullOrWhiteSpace(defaultNamingContext))
            {
                return new DomainUserInfo();
            }

            using var entry = new DirectoryEntry($"LDAP://{defaultNamingContext}");
            using var searcher = new DirectorySearcher(entry)
            {
                Filter = $"(&(objectCategory=person)(objectClass=user)(sAMAccountName={EscapeLdapFilterValue(accountName)}))",
                SearchScope = SearchScope.Subtree,
                PageSize = 1
            };
            searcher.PropertiesToLoad.Add("displayName");
            searcher.PropertiesToLoad.Add("mail");
            searcher.PropertiesToLoad.Add("department");
            searcher.PropertiesToLoad.Add("title");

            var result = searcher.FindOne();
            if (result is null)
            {
                return new DomainUserInfo();
            }

            return new DomainUserInfo
            {
                DisplayName = ReadSearchProperty(result, "displayName"),
                Email = ReadSearchProperty(result, "mail"),
                Department = ReadSearchProperty(result, "department"),
                Title = ReadSearchProperty(result, "title")
            };
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Failed to look up AD attributes for {User}", rawUser);
            return new DomainUserInfo();
        }
    }

    private static string ReadSearchProperty(SearchResult result, string name)
    {
        if (result.Properties.Contains(name) && result.Properties[name].Count > 0)
        {
            return Convert.ToString(result.Properties[name][0]) ?? "";
        }
        return "";
    }

    private static string EscapeLdapFilterValue(string value)
    {
        return value
            .Replace("\\", "\\5c", StringComparison.Ordinal)
            .Replace("*", "\\2a", StringComparison.Ordinal)
            .Replace("(", "\\28", StringComparison.Ordinal)
            .Replace(")", "\\29", StringComparison.Ordinal)
            .Replace("\0", "\\00", StringComparison.Ordinal);
    }

    private static string EncodeHeaderValue(string value)
    {
        var bytes = System.Text.Encoding.UTF8.GetBytes(value);
        var builder = new System.Text.StringBuilder(bytes.Length * 3);
        foreach (var b in bytes)
        {
            if ((b >= 'A' && b <= 'Z') ||
                (b >= 'a' && b <= 'z') ||
                (b >= '0' && b <= '9') ||
                b == '-' || b == '_' || b == '.' || b == '~')
            {
                builder.Append((char)b);
            }
            else
            {
                builder.Append('%');
                builder.Append(b.ToString("X2"));
            }
        }
        return builder.ToString();
    }

    private void AddAuthHeaders(HttpRequestMessage request, string rawUser, string clientIp, DomainUserInfo info)
    {
        var headerName = config["Proxy:HeaderName"] ?? "X-Remote-User";
        request.Headers.Remove(headerName);
        request.Headers.TryAddWithoutValidation(headerName, rawUser);
        request.Headers.Remove("X-Forwarded-User");
        request.Headers.TryAddWithoutValidation("X-Forwarded-User", rawUser);
        request.Headers.Remove("X-Forwarded-For");
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", clientIp);
        AddOptionalHeader(request, "X-Remote-Display-Name", info.DisplayName);
        AddOptionalHeader(request, "X-Remote-Mail", info.Email);
        AddOptionalHeader(request, "X-Remote-Department", info.Department);
        AddOptionalHeader(request, "X-Remote-Title", info.Title);
    }

    private static void AddOptionalHeader(HttpRequestMessage request, string name, string value)
    {
        request.Headers.Remove(name);
        if (!string.IsNullOrWhiteSpace(value))
        {
            request.Headers.TryAddWithoutValidation(name, EncodeHeaderValue(value));
        }
    }

    private void ApplyCorsHeaders(HttpListenerRequest request, HttpListenerResponse response)
    {
        var origin = request.Headers["Origin"] ?? "";
        if (string.IsNullOrWhiteSpace(origin) || !CorsOriginAllowed(origin))
        {
            return;
        }
        response.Headers["Access-Control-Allow-Origin"] = origin;
        response.Headers["Access-Control-Allow-Credentials"] = "true";
        response.Headers["Vary"] = "Origin";
        response.Headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS";
        response.Headers["Access-Control-Allow-Headers"] = "Content-Type,Accept";
    }

    private bool CorsOriginAllowed(string origin)
    {
        var values = (config["Proxy:CorsAllowedOrigins"] ?? "")
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        return values.Any(item => string.Equals(item, origin, StringComparison.OrdinalIgnoreCase));
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

    private sealed class DomainUserInfo
    {
        public string DisplayName { get; init; } = "";
        public string Email { get; init; } = "";
        public string Department { get; init; } = "";
        public string Title { get; init; } = "";
    }
}
