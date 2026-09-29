# 奇安信攻防社区-「JavaWeb审计盲点」存储过程里的 SQL 注入
> QIANXIN Team
> 来源：https://forum.butian.net/share/5079

# 0x00 被遗漏的审计对象

对于一个典型的JavaWeb项目，在审计时，我们的常见的思路一般如下:

```Plain
拦截器/过滤器 → Controller → Service → Mapper/DAO → 常见的ORM框架配置（MyBatis XML等）
```

如果想挖掘SQL注入风险，一般会检索类似`executeQuery`、`${}`、`Statement`的关键字,然后沿着参数链一路追踪。在这个熟悉的审计清单里,貌似基本没有关注过项目里的 `.sql` 文件，一般都默认为项目的基础配置文件，就直接忽略掉了。

实际上：

-   项目的 SQL 不只在 Mapper 和代码里,**还有一部分在部署时就"安装"进了数据库**,以存储过程、函数、触发器的形态常驻
-   这部分代码并不会**不参与编译**
-   它由 DBA 或发布脚本部署,可能从部署至今就没人review过，版本甚至和仓库里的 `.sql` 源文件都不一致

`.sql` 文件部署进库的对象有很多(函数、触发器、视图、定时任务都在其中),其中攻击面最直接的就是**存储过程。**

其在应用中通过 CALL 方法显式调用，参数能从 HTTP 入口一路直达过程形参，是距离外部攻击者最近的一条链路。

下面看看其中的审计盲点。

# 0x01 存储过程中的SQL注入

## 1.1 相关案例

首先看一个具体的例子，在项目的sql文件中注册了find\_user\_vuln这个存储过程：

```SQL
DROP PROCEDURE IF EXISTS find_user_vuln;
DELIMITER //
CREATE PROCEDURE find_user_vuln(IN p_name VARCHAR(64))
BEGIN
  SET @sql = CONCAT('SELECT id, name, password, role FROM users WHERE name = ''', p_name, '''');
  PREPARE stmt FROM @sql;
  EXECUTE stmt;
  DEALLOCATE PREPARE stmt;
END //
DELIMITER ;
```

一般来说这些sql文件的运行周期如下：

```Plain
.sql 文件 ──(DBA 执行 / 发布脚本 / Flyway·Liquibase 迁移)──> 数据库编译并保存 PROCEDURE 对象
```

-   `.sql` 文件就类似\*\*安装包，\*\*执行一次，存储过程就会被"装进"数据库
-   在这之后，数据库里的 PROCEDURE 对象与文件**再无关系**,文件删了照样运行

这里通过数据库的元数据查看相关的存储过程是否已经“安装进了数据库”：

```Java
SELECT ROUTINE_SCHEMA, ROUTINE_NAME, DEFINER FROM information_schema.ROUTINES WHERE ROUTINE_TYPE='PROCEDURE';
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/08/attach-9d4a17c55bafc43844fd36305f2add625d3b2ac1.png)

确定以后，看看具体在代码中是怎么调用这个存储过程的。

这里以mybatis为例，通过call function的方式即可调用对应的存储过程：

```Java
@Select("{call find_user_vuln(#{name, mode=IN, jdbcType=VARCHAR})}")
@Options(statementType = StatementType.CALLABLE)
List<User> findByNameVuln(String name);
```

同理，通过jdbc调用也是一样的：

```Java
List<User> result = new ArrayList<>();
try (Connection conn = dataSource.getConnection();
     CallableStatement cs = conn.prepareCall("{call find_user_vuln(?)}")) {
    cs.setString(1, name);          
    try (ResultSet rs = cs.executeQuery()) {
        while (rs.next()) {
            User u = new User();
            u.setId(rs.getInt("id"));
            u.setName(rs.getString("name"));
            u.setPassword(rs.getString("password"));
            u.setRole(rs.getString("role"));
            result.add(u);
        }
    }
}
return result;
```

那么上述的代码是否存在安全风险呢？

## 1.2 风险复现

从上面的代码片段看，追踪到 `{call proc(?)}` ，可能很多时候这个 sink 基本就判定"已参数化,安全"。

下面直接看看具体的接口调用：

正常情况下查询alice，成功返回具体的用户信息：

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/08/attach-c2d15aab2215fe202f6f229023462bbac66ae33e.png)

当尝试进行SQL注入时，发现成功执行了对应拼接的sql：

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/08/attach-2fbdd37721d50e949195bc5c325e42804a49b8e3.png)

从代码上看，已经做了参数化查询：

```Java
cs = conn.prepareCall("{call find_user(?)}");
cs.setString(1, userInput);
```

确实没发现可能存在SQL注入的点，为什么会存在SQL注入的风险呢？

如果刚刚有关注具体的.sql里的sql片段的话，会发现有这么一段：

```Java
SET @sql = CONCAT('SELECT id, name, password, role FROM users WHERE name = ''', p_name, '''');
```

具体的含义是把**用户传入的 p\_name 用 CONCAT 直接拼进一段 SQL 字符串**（''' 是转义后的单引号，用来给名字包上引号），存进变量 @sql，然后被 PREPARE 当 SQL 执行\*\*。\*\*

这里实际上p\_name是通过动态拼接的方式引入的，所以正常情况下，同样会存在SQL注入的风险。

如果相关sql代码替换成如下（这里为了区分命名为find\_user\_safe）：

```SQL
DROP PROCEDURE IF EXISTS find_user_safe;
DELIMITER //
CREATE PROCEDURE find_user_safe(IN p_name VARCHAR(64))
BEGIN
  SELECT id, name, password, role FROM users WHERE name = p_name;
END //
DELIMITER ;
```

因为没有拼接的场景，自然而然也就没有了SQL注入的风险：

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/08/attach-32ec1bd44602147ff27da551ed52f15a33477397.png)

但是以mybatis为例，从代码上看，跟之前的漏洞代码是一模一样的：

```Java
@Select("{call find_user_safe(#{name, mode=IN, jdbcType=VARCHAR})}")
@Options(statementType = StatementType.CALLABLE)
List<User> findByNameSafe(String name);
```

即使调用处完全规范,如果不仔细看具体的sql定义，很容易就形成审计了盲区。尤其是类似表名、列名、`ORDER BY` 字段、`LIMIT` 后的数字等**标识符类参数**不能用占位符。如果它们来自用户输入并在过程体/代码中拼接,是注入高发区。

## 1.3 常见误区

基于上面的例子，在审计时经常会存在一些误区：

-   **项目中使用了存储过程，所以不存在 SQL 注入**

存储过程只是把 SQL 从应用代码挪进了数据库。**注入的本质是"用户输入被拼进 SQL 文本并被解析执行",这个行为发生在哪一层,跟它在哪里被执行没有关系。** 过程体内部照样可以拼字符串、照样可以动态执行。

-   **调用处用了参数化绑定,就安全了**

参数化绑定(`?` 占位符、`#{}`)只保证**值进入过程的那一步**不被当作 SQL 解析。值进入过程之后,过程体拿它干什么，是绑定变量还是拼接字符串，调用处完全不知情。

-   **审计代码就够了**

如果审计 Java 代码,看到的只是是一行 `{call find_user(?)}`，但是实际上`.sql`文件里仍使用拼接的方式进行调用，参数绑定并不生效。

# 0x02 常见的调用方式

审计的方法也比较简单，首先从 .sql 文件(或数据库元数据)提取存储过程清单 + 参数签名，在代码中全局搜索过程名，调用具体的调用点，然后沿着调用链回溯，判断参数是否可控，且是否经过白名单类的安全处理即可。

下面整理下具体的特征：

## 2.1 常见的存储过程调用代码

审计时按可以按照过程名全局搜索,命中哪种写法就对应哪种调用方式:

-   **JDBC 原生**

```Java
CallableStatement cs = conn.prepareCall("{call proc_name(?, ?)}");
cs.setString(1, in);
cs.registerOutParameter(2, Types.INTEGER);
cs.execute();
```

**关键词**:`prepareCall`、`CallableStatement`

-   **MyBatis**

```Plain
<select id="doIt" statementType="CALLABLE" resultType="map">
  {call proc_name(
    #{inParam, mode=IN,  jdbcType=VARCHAR},
    #{outParam, mode=OUT, jdbcType=INTEGER})}
</select>
```

**关键词**:`statementType="CALLABLE"`、`{call`

-   **Spring**

```Java
SimpleJdbcCall call = new SimpleJdbcCall(dataSource).withProcedureName("proc_name");
Map<String, Object> out = call.execute(Map.of("inParam", "v"));
```

**关键词**:`SimpleJdbcCall`、`StoredProcedure`(Spring 的抽象类)

-   **JPA / Hibernate**

```Java
StoredProcedureQuery q = em.createStoredProcedureQuery("proc_name");
q.registerStoredProcedureParameter("inParam", String.class, ParameterMode.IN);
```

**关键词**:`createStoredProcedureQuery`、`@NamedStoredProcedureQuery`

无论哪种方式,调用处的安全性判断标准主要是看：

**值走占位符/绑定,还是跟具体的 SQL 文本有关，如果跟文本有关，那么就需要详细检查具体的sql定义。**

## 2.2 .sql定义中存在拼接的场景

主要是检查sql中动态执行写法(注入点)、审计检索词、以及绑定变量的写法。下面是一些常见数据库的总结：

-   **Oracle**

**拼接方式:**

```SQL
EXECUTE IMMEDIATE 'SELECT ... WHERE name = ''' || p_name || '''';

```

**关键词**:`EXECUTE IMMEDIATE`、`DBMS_SQL`、`||`(配合上下文)

**绑定变量（安全）:**

```SQL
EXECUTE IMMEDIATE 'SELECT ... WHERE name = :1' USING p_name;
```

-   **MySQL**

**拼接方式:**

```SQL
SET @sql = CONCAT('SELECT ... WHERE name = ''', p_name, '''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
```

**关键词**:`PREPARE`、`CONCAT`、`EXECUTE`(过程体内)、`SET @`

**绑定变量（安全）:**

存储过程中的 `PREPARE` 是**支持占位符的**:

```SQL
SET @sql = 'SELECT ... WHERE name = ?';
PREPARE stmt FROM @sql;
SET @name = p_name;
EXECUTE stmt USING @name;
```

-   **SQL Server**

**拼接方式:**

```SQL
EXEC('SELECT ... WHERE name = ''' + @name + '''');

EXEC sp_executesql N'SELECT ... WHERE name = ''' + @name + '''';
```

**关键词**:`EXEC(`、`EXECUTE(`、`sp_executesql`、`+ @`

**绑定变量（安全）:**

**`sp_executesql`** **支持参数化:**

```SQL
EXEC sp_executesql
  N'SELECT ... WHERE name = @name',
  N'@name NVARCHAR(50)',
  @name = @name;
```
