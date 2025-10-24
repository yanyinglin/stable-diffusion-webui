# SD WebUI Proxy Kubernetes 部署指南

本文档介绍如何在 Kubernetes 集群中部署 SD WebUI 代理服务。

## 文件说明

- `k8s-deployment.yaml` - 完整的部署配置（包含 Deployment、Service、Ingress、HPA）
- `k8s-deploy.sh` - 自动化部署脚本

## 快速部署

### 1. 使用部署脚本（推荐）

```bash
# 使用默认域名
./k8s-deploy.sh

# 指定域名
./k8s-deploy.sh sd-webui.example.com
```

### 2. 手动部署

```bash
# 部署应用（使用 pipecache 命名空间）
kubectl apply -f k8s-deployment.yaml
```

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SD_API_URL` | `http://sd-api-service:7860` | 后端 SD API 服务地址 |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | 服务器监听地址 |
| `GRADIO_SERVER_PORT` | `7860` | 服务器端口 |
| `SD_API_TIMEOUT` | `600` | API 请求超时时间（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 资源配置

- **CPU 请求**: 100m
- **CPU 限制**: 500m
- **内存请求**: 256Mi
- **内存限制**: 512Mi

### 副本和扩缩容

- **最小副本数**: 2
- **最大副本数**: 10
- **CPU 扩缩容阈值**: 70%
- **内存扩缩容阈值**: 80%

## 服务访问

### Ingress 配置

部署后可通过 Ingress 访问服务：

```yaml
# 需要修改的配置
spec:
  rules:
  - host: sd-webui.yourdomain.com  # 替换为您的域名
```

### 端口转发（测试用）

```bash
# 端口转发到本地
kubectl port-forward service/sd-webui-proxy-service 7860:7860 -n sd-webui

# 访问 http://localhost:7860
```

## 监控和管理

### 查看服务状态

```bash
# 查看 Pod 状态
kubectl get pods -n pipecache

# 查看服务
kubectl get svc -n pipecache

# 查看 Ingress
kubectl get ingress -n pipecache

# 查看 HPA 状态
kubectl get hpa -n pipecache
```

### 查看日志

```bash
# 查看所有 Pod 日志
kubectl logs -f deployment/sd-webui-proxy -n pipecache

# 查看特定 Pod 日志
kubectl logs -f <pod-name> -n pipecache
```

### 扩缩容

```bash
# 手动扩缩容
kubectl scale deployment sd-webui-proxy --replicas=5 -n pipecache

# 查看扩缩容状态
kubectl get hpa sd-webui-proxy-hpa -n pipecache
```

## 故障排除

### 常见问题

1. **Pod 启动失败**
   ```bash
   kubectl describe pod <pod-name> -n pipecache
   kubectl logs <pod-name> -n pipecache
   ```

2. **服务无法访问**
   ```bash
   # 检查服务配置
   kubectl get svc sd-webui-proxy-service -n pipecache -o yaml
   
   # 检查 Ingress 配置
   kubectl describe ingress sd-webui-proxy-ingress -n pipecache
   ```

3. **后端 API 连接失败**
   ```bash
   # 检查环境变量配置
   kubectl describe deployment sd-webui-proxy -n pipecache
   
   # 检查网络连通性
   kubectl exec -it <pod-name> -n pipecache -- curl http://sd-api-service:7860/sdapi/v1/progress
   ```

### 健康检查

```bash
# 检查健康状态
kubectl get pods -n pipecache -o wide

# 检查就绪状态
kubectl get pods -n pipecache -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'
```

## 更新和升级

### 更新镜像

```bash
# 更新镜像版本
kubectl set image deployment/sd-webui-proxy sd-webui-proxy=k.harbor.siat.ac.cn/pels/sd-webui:v0.11 -n pipecache

# 查看更新状态
kubectl rollout status deployment/sd-webui-proxy -n pipecache
```

### 回滚

```bash
# 查看版本历史
kubectl rollout history deployment/sd-webui-proxy -n pipecache

# 回滚到上一版本
kubectl rollout undo deployment/sd-webui-proxy -n pipecache

# 回滚到指定版本
kubectl rollout undo deployment/sd-webui-proxy --to-revision=2 -n pipecache
```

## 清理资源

```bash
# 删除部署
kubectl delete -f k8s-deployment.yaml
```

## 安全建议

1. **使用 HTTPS**: 在生产环境中配置 TLS 证书
2. **网络策略**: 配置 NetworkPolicy 限制网络访问
3. **资源限制**: 根据实际需求调整资源限制
4. **镜像安全**: 定期更新基础镜像和依赖
5. **密钥管理**: 使用 Kubernetes Secrets 管理敏感信息

## 性能优化

1. **调整副本数**: 根据负载调整最小/最大副本数
2. **资源调优**: 根据实际使用情况调整 CPU/内存限制
3. **缓存配置**: 考虑添加 Redis 等缓存服务
4. **CDN 加速**: 对静态资源使用 CDN 加速
