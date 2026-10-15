# WPA_SUPPLICANT源码分析笔记之WiFi扫描
> 岁月别催
> 来源：https://www.iotsec-zone.com/article/124

supplicant接收到”SCAN”命令后，

由wpa_supplicant_ctrl_iface_process处理。（处理各种supplicant收到的命令，参数char* buf存放扫描命令）
![0.png](https://www.iotsec-zone.com/images/MdImg/5a79ebe5f2935cd0c874b6552dba5e35.png)

wpas_ctrl_scan // 处理扫描命令（处理各种scan参数并执行扫描）

![1.png](https://www.iotsec-zone.com/images/MdImg/ee3938394c7486056334a1f40ce7fa22.png)

wpa_supplicant_req_scan（扫描任务的控制）

![2.png](https://www.iotsec-zone.com/images/MdImg/efd6ad1fcebd85a414474f843b5cc2b9.png)

wpa_supplicant_scan

判断网络状态→判断是否正在进行扫描→增加扫描限制条件（指定ssid、修改AP_SCAN为0（使用驱动扫描）、wifi p2p、pno扫描、设置最大ssid数量默认16、直接连接指定ssid等）→开始扫描
![3.png](https://www.iotsec-zone.com/images/MdImg/65348a8b11001cd98e522365e8436178.png)
![4.png](https://www.iotsec-zone.com/images/MdImg/e3cd847db5bf3f06de66ef99bdd65ace.png)

wpa_supplicant_trigger_scan（注册扫描任务后等待内核无线电模块操作空闲开始扫描）

![5.png](https://www.iotsec-zone.com/images/MdImg/6eb9b71747b6badd937ac4f025187468.png)
![6.png](https://www.iotsec-zone.com/images/MdImg/e102e9594bb16f6c204258ec86d25826.png)
wpas_trigger_scan_cb

![7.png](https://www.iotsec-zone.com/images/MdImg/3881ef40192c48eef09777f29b075ccd.png)

wpa_drv_scan // wpas->driver->scan2调用到driver_nl80211_scan

![8.png](https://www.iotsec-zone.com/images/MdImg/06d58d8646ec0eb7a1d49840a65bac7c.png)

![9.png](https://www.iotsec-zone.com/images/MdImg/ef01638dc46ecaedd26994bf8e037918.png)

wpa_driver_nl80211_scan

![10.png](https://www.iotsec-zone.com/images/MdImg/5267de3ffddc20c95bc796e9c4b8cbea.png)

send_and_recv_msgs

该函数是send_and_recv的封装

scan2函数功能为基于netlink的nl80211编程，常用步骤为：

nl_socket_alloc();                       //生成netlink的socket（netlink相关内容参考上文给出的介绍）

***********i802_init

nl_socket_set_buffer_size(state->nl_sock, 8192, 8192);                //调整缓存大小

***********nl80211_register_eloop_read

genl_connect(state->nl_sock)          //socket和内核连接（注意，这里用的genl的函数封装，具体可查参考（上文给出的地址））

************nl_create_handle

genl_ctrl_resolve(state->nl_sock, "nl80211");                                    //genl的概念，向内核查询一下协议族的标志

************wpa_driver_nl80211_init_nl_global

msg = nlmsg_alloc();          //生成帧的内存空间

************nl80211_cmd_msg

cb = nl_cb_alloc(iw_debug ? NL_CB_DEBUG : NL_CB_DEFAULT);      //生成回调函数

genlmsg_put(msg, 0, 0, state->nl80211_id, 0, cmd->nl_msg_flags, cmd->cmd, 0);                             //往刚生成的帧中填充头部信息 

*************nl80211_cm

nla_put_u32(msg, NL80211_ATTR_IFINDEX, devidx);                //向刚生成的帧内部添加一个属性值

************** 上述nl80211_cmd_msg

nl_socket_set_cb(state->nl_sock, s_cb);                                            //设置回调函数

nl_send_auto_complete(state->nl_sock, msg);                                 //发送刚生成的帧给内核。自此，内核当收到该请求时就会执行在帧中填充的命令索引和参数。比如搜索无线网，帧中就会填充scan命令对应的索引和要扫描的信道作为参数。

**************send_and_recv

while (err > 0)nl_recvmsgs(state->nl_sock, cb);                                                 //等待接收内核的反馈

**************send_and_recv

进入libnl：

nl_send_auto_complete→nl_send_auto→nl_send→nl_send_iovec→nl_sendmsg→sendmsg

进入内核：

触发扫描的内核调用过程

SYSCALL_DEFINE3(sendmsg, int, fd, struct msghdr __user *, msg, unsigned,flags)

__sys_sendmsg (net\socket.c)

多次封装转入调用：

sock_sendmsg

sock_sendmsg_nosec

__sock_sendmsg

__sock_sendmsg_nosec (sock->ops->sendmsg调用netlink_sendmsg)

netlink_sendmsg

netlink_unicast

netlink_unicast_kernel （nlk->netlink_rcv调用genl_rcv）

genl_rcv （cb 为genl_rcv_msg）

genl_rcv_msg （ops->doit调用到nl80211_trigger_scan）

nl80211_trigger_scan （net\wireless\nl80211.c)

下列针对扫描流程的文字解释以及进入来自（[https://www.codenong.com/cs106724317/](https://www.codenong.com/cs106724317/)）

◆上层发起一次scan命令->wifi进行各个信道的sacn->驱动包扫描结果存储在scanned_queue->扫面完成->通过rtw_cfg80211_surveydone_event_callback（cfg80211_inform_bss_frame）把扫描的ap结果通知内核net/wireless/scan.c->通过rtw_indicate_scan_done（cfg80211_scan_done）通知内核、上层扫描结束。

◆Wifi驱动每次发起扫面前，都会检查上次扫描到的ap到现在的时间是否超过20s（SCANQUEUE_LIFETIME），若超过20s，就会调用rtw_list_delete把ap从scanned_queue中去掉，接下来再扫面到新的ap时，再加入scanned_queue。

◆每次扫描完所有信道后，会再次扫描一个信道，连接ap的情况下，扫描的信道为所连接ap的信道，没连接ap的情况下，为最后一个扫描信道。

◆对于接收到的beacon帧，由OnBeacon处理，只有在扫描状态的时候，beacon的ap才会被加入到scanned_queue，其它情况根据WIFI_FW状态进行不同操作，有触发start_clnt_auth，有更新ap信息等操作。

◆net/wireless中使用bss_list保存扫描到的ap结果，扫描结束后，应用层通过NL80211_CMD_GET_SCAN命令，由内核nl80211_dump_scan函数把结果发送给应用层，内核中保存ap有效时间为3s，超过3s该ap的信息会从bss_lis移除。

◆supplicant中通过wpa_s->bss保存扫描的ap，如果一个ap在180s（DEFAULT_BSS_EXPIRATION_AGE）内没有更新，就会删除该ap，每10s进行一次检测，由wpa_bss_timeout函数检查。

新人第一在论坛发帖，如有错误之处还请大佬指出，欢迎共同探讨问题。
