"""
Redis 集群状态检查脚本
"""

import redis

redis_host = "192.168.1.86"
redis_port = 6379

print("="*60)
print("Redis 集群状态检查")
print("="*60)

try:
    # 连接 Redis
    client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )
    
    # 获取集群信息
    print("\n[集群信息]")
    cluster_info = client.execute_command('CLUSTER', 'INFO')
    print(cluster_info)
    
    # 获取集群节点信息
    print("\n[集群节点]")
    cluster_nodes = client.execute_command('CLUSTER', 'NODES')
    print(cluster_nodes)
    
    # 解析集群状态
    print("\n[状态分析]")
    if "cluster_state:ok" in cluster_info:
        print("✓ 集群状态正常")
    else:
        print("✗ 集群状态异常")
        
    if "cluster_slots_assigned:16384" in cluster_info:
        print("✓ 所有 hash slots 已分配")
    else:
        print("✗ Hash slots 未完全分配")
        print("  这将导致 'Hash slot not served' 错误")
    
    # 统计节点数
    node_count = cluster_nodes.count('\n')
    print(f"✓ 集群节点数: {node_count}")
    
    if node_count < 6:
        print("  警告: Redis 集群建议至少 6 个节点（3主3从）")
    
except Exception as e:
    print(f"\n✗ 检查失败: {e}")
    error_msg = str(e)
    
    if "CLUSTERDOWN" in error_msg or "Hash slot not served" in error_msg:
        print("\n诊断结果:")
        print("="*60)
        print("✗ Redis 集群未正确初始化")
        print("\n可能的原因:")
        print("  1. 集群节点未全部启动")
        print("  2. Hash slots 未分配")
        print("  3. 集群配置错误")
        print("\n解决方案:")
        print("\n方案 1: 修复集群")
        print("  使用 redis-cli 重新初始化集群:")
        print("  redis-cli --cluster create <node1:port> <node2:port> ... --cluster-replicas 1")
        print("\n方案 2: 使用单机模式")
        print("  修改 config/config.ini:")
        print("  [redis]")
        print("  mode = single")
        print("\n方案 3: 连接到非集群 Redis")
        print("  如果有其他 Redis 实例，修改配置连接到那个实例")
        print("="*60)
