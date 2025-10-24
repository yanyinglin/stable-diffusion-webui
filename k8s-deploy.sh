#!/bin/bash

# SD WebUI Proxy Kubernetes Deployment Script
# 使用方法: ./k8s-deploy.sh [domain]

set -e

NAMESPACE="pipecache"
DOMAIN=${1:-sd-webui.yourdomain.com}

echo "🚀 开始部署 SD WebUI Proxy 到 Kubernetes"
echo "📦 Namespace: $NAMESPACE"
echo "🌐 Domain: $DOMAIN"

# 检查 kubectl 是否可用
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl 未安装或不在 PATH 中"
    exit 1
fi

# 检查集群连接
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ 无法连接到 Kubernetes 集群"
    exit 1
fi

echo "✅ Kubernetes 集群连接正常"

# 检查 namespace 是否存在
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "❌ Namespace '$NAMESPACE' 不存在，请先创建"
    exit 1
fi

echo "✅ Namespace '$NAMESPACE' 存在"

# 更新域名
echo "🌐 更新 Ingress 域名: $DOMAIN"
sed "s/sd-webui.yourdomain.com/$DOMAIN/g" k8s-deployment.yaml > k8s-deployment-temp.yaml

# 部署应用
echo "🚀 部署 SD WebUI Proxy"
kubectl apply -f k8s-deployment-temp.yaml

# 清理临时文件
rm -f k8s-deployment-temp.yaml

# 等待部署完成
echo "⏳ 等待部署完成..."
kubectl rollout status deployment/sd-webui-proxy -n $NAMESPACE --timeout=300s

# 显示服务状态
echo "📊 服务状态:"
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get ingress -n $NAMESPACE

echo "✅ 部署完成!"
echo ""
echo "🔗 访问地址: http://$DOMAIN"
echo "📊 查看日志: kubectl logs -f deployment/sd-webui-proxy -n $NAMESPACE"
echo "🛠️  管理命令:"
echo "   - 查看 Pod: kubectl get pods -n $NAMESPACE"
echo "   - 查看服务: kubectl get svc -n $NAMESPACE"
echo "   - 查看 Ingress: kubectl get ingress -n $NAMESPACE"
echo "   - 删除部署: kubectl delete -f k8s-deployment.yaml"
