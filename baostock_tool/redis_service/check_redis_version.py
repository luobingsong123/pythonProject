"""
Redis 版本诊断脚本
检查当前安装的 redis 和 redis-py-cluster 版本
"""

import sys

print("="*60)
print("Redis 版本诊断")
print("="*60)

# 检查 redis 包版本
try:
    import redis
    print(f"\n✓ redis 包已安装")
    print(f"  版本: {redis.__version__}")
    print(f"  路径: {redis.__file__}")
except ImportError as e:
    print(f"\n✗ redis 包未安装: {e}")

# 检查 redis-py-cluster 包
try:
    import rediscluster
    print(f"\n✓ redis-py-cluster 包已安装")
    print(f"  路径: {rediscluster.__file__}")
    # 尝试获取版本
    try:
        print(f"  版本: {rediscluster.__version__}")
    except:
        print(f"  版本: 未知")
except ImportError as e:
    print(f"\n✗ redis-py-cluster 包未安装: {e}")

# 检查 redis 内置集群支持
try:
    from redis.cluster import RedisCluster
    print(f"\n✓ redis-py 内置集群支持可用")
    print(f"  (redis >= 4.0.0)")
except ImportError as e:
    print(f"\n✗ redis-py 内置集群支持不可用")
    print(f"  (redis < 4.0.0)")

print("\n" + "="*60)
print("解决方案")
print("="*60)

try:
    import redis
    version = tuple(map(int, redis.__version__.split('.')))
    
    if version >= (4, 0, 0):
        print("\n推荐方案 1: 使用 redis-py 内置集群支持")
        print("  已支持，无需额外安装")
        print("\n推荐方案 2: 降级 redis 到 3.x 并使用 redis-py-cluster")
        print("  pip uninstall redis")
        print("  pip install redis==3.5.3")
        print("  pip install redis-py-cluster")
    else:
        print("\n推荐方案: 使用 redis-py-cluster")
        print("  当前配置已支持")
        print("\n或者升级到 redis >= 4.0.0 获得内置集群支持:")
        print("  pip uninstall redis-py-cluster")
        print("  pip install --upgrade redis")
        
except Exception as e:
    print(f"\n无法确定推荐方案: {e}")

print("\n" + "="*60)
print("配置文件设置")
print("="*60)
print("\n如果你的 Redis 是集群模式，请在 config/config.ini 中设置:")
print("  [redis]")
print("  mode = cluster")
print("\n如果你的 Redis 是单机模式，请设置:")
print("  [redis]")
print("  mode = single")
print("="*60)
