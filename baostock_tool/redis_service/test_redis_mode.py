"""
Redis 模式检测脚本
检查 Redis 是单机模式还是集群模式
"""

import redis
import sys

# 从配置文件读取 Redis 连接信息
redis_host = "192.168.1.86"
redis_port = 6379
redis_db = 0

print("="*60)
print("Redis 模式检测")
print("="*60)
print(f"目标: {redis_host}:{redis_port}")

# 测试 1: 尝试单机模式连接
print("\n[测试 1] 尝试单机模式连接...")
try:
    client = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True
    )
    
    # 测试 PING
    result = client.ping()
    print(f"✓ 单机模式 PING 成功: {result}")
    
    # 测试 INFO
    info = client.info("server")
    print(f"✓ 获取服务器信息成功")
    print(f"  Redis 版本: {info.get('redis_version')}")
    print(f"  运行模式: {info.get('redis_mode')}")
    
    # 检查是否启用了集群
    cluster_info = client.info("cluster")
    cluster_enabled = cluster_info.get('cluster_enabled', 0)
    print(f"  集群启用: {'是' if cluster_enabled else '否'}")
    
    # 尝试执行一个简单的命令
    print("\n[测试 2] 尝试执行简单命令...")
    client.set("test_key", "test_value")
    value = client.get("test_key")
    print(f"✓ SET/GET 测试成功: {value}")
    client.delete("test_key")
    
    # 尝试执行 Stream 命令
    print("\n[测试 3] 尝试执行 Stream 命令...")
    try:
        # 尝试写入 Stream
        msg_id = client.xadd("test_stream", {"data": "test"})
        print(f"✓ XADD 测试成功: {msg_id}")
        
        # 读取 Stream
        messages = client.xread({"test_stream": "0"}, count=1)
        print(f"✓ XREAD 测试成功: {len(messages)} 条消息")
        
        # 删除测试 Stream
        client.delete("test_stream")
        print("✓ Stream 操作正常")
        
    except Exception as e:
        print(f"✗ Stream 操作失败: {e}")
        error_msg = str(e)
        if "CLUSTERDOWN" in error_msg or "MOVED" in error_msg:
            print("  检测到集群相关错误")
    
    client.close()
    
    print("\n" + "="*60)
    print("结论")
    print("="*60)
    if cluster_enabled:
        print("⚠ Redis 启用了集群模式，但可能集群未正确初始化")
        print("\n建议:")
        print("  1. 检查 Redis 集群是否正确初始化")
        print("  2. 检查集群节点是否都在线")
        print("  3. 在配置文件中设置 mode = cluster")
    else:
        print("✓ Redis 是单机模式")
        print("\n建议:")
        print("  在 config/config.ini 中设置:")
        print("  [redis]")
        print("  mode = single")
    print("="*60)
    
except redis.exceptions.ConnectionError as e:
    print(f"✗ 连接失败: {e}")
    print("\n可能的原因:")
    print("  1. Redis 服务未启动")
    print("  2. 网络连接问题")
    print("  3. 防火墙阻止连接")
    
except Exception as e:
    print(f"✗ 测试失败: {e}")
    error_msg = str(e)
    
    if "CLUSTERDOWN" in error_msg:
        print("\n检测到集群模式，但集群未正确初始化")
        print("\n建议:")
        print("  1. 检查 Redis 集群状态")
        print("  2. 确保所有集群节点都在线")
        print("  3. 使用 redis-cli 检查: redis-cli -h 192.168.1.86 -p 6379 cluster info")
    elif "MOVED" in error_msg or "ASK" in error_msg:
        print("\n检测到集群重定向错误")
        print("这是一个 Redis 集群")
