# EnvPortal

**EnvPortal** (formerly *組織环境导航系统*) is a lightweight, zero-dependency, ultra-portable Environment and RDP metadata navigation dashboard.

Designed specifically for strict corporate environments where tools like Tomcat, Python, Node, and external APIs are unavailable or constrained by policies. EnvPortal achieves a fully functional Backend+Frontend real-time visualization application using **100% Native Windows PowerShell**.

## 🚀 Features

- **Portability First**: Zero dependencies. Runs completely out of the box on Windows environments utilizing the natively embedded PowerShell HTTP framework.  
- **Gatekeeper Authentication**: Data and RDP Management routes are heavily guarded by server-side validated prompt flows with **15-minute persistent localStorage sessions**—maximizing security against shoulder-surfing while minimizing frustration.
- **Enterprise Status Real-Time Pings**: A proprietary internal backend proxy dynamically bridges and bypasses browser CORS locks to natively SSL-scan environment endpoints and display live HTTP 200 uptime statuses natively aligned in edge headers.
- **RDP Center**: Separate domain routing with independent data persistence (`rdp.csv`) to manage critical internal remote network endpoints distinct from generic URLs (`data.csv`).
- **One-Click Deploy**: Double-click `start.bat` to instantly raise the web socket and launch the browser natively.

## 🛠️ Usage

1. Do not install any databases, runtimes, or libraries.
2. Unzip the artifact into any folder.
3. Double-click `start.bat`. 

**The local system will instantly bind to `localhost:8080` and launch the app in your default browser.** 

All edited artifacts will be synchronized immediately back to the local `csv` registry stores with smart encoding guarantees.
