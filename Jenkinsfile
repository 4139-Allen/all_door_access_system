// ============================================================
// 门禁管理系统 - Jenkins CI/CD Pipeline
// 方案：镜像仓库（阿里云容器镜像服务）
// ============================================================

pipeline {
    agent any

    environment {
        // ---- 阿里云镜像仓库 ----
        REGISTRY        = 'crpi-m44y6y44d0d23rbk.cn-hongkong.personal.cr.aliyuncs.com'
        NAMESPACE       = 'door-system'
        IMAGE_BACKEND   = "${REGISTRY}/${NAMESPACE}/door-fastapi"
        IMAGE_FRONTEND  = "${REGISTRY}/${NAMESPACE}/door-frontend"
        IMAGE_TAG       = "build-${BUILD_NUMBER}"

        // ---- GitHub 仓库 ----
        GIT_URL         = 'https://github.com/4139-Allen/all_door_access_system.git'

        // ---- 正式服务器（Server B）- 改成你的 ----
        DEPLOY_HOST     = 'root@47.242.60.67'
        DEPLOY_PATH     = '/opt/door_access_system'
    }

    parameters {
        choice(name: 'RUN_TESTS', choices: ['yes', 'no'], description: '部署前跑测试？')
        string(name: 'BRANCH', defaultValue: 'main', description: '分支')
    }

    triggers {
        githubPush()
    }

    stages {
        // ============================================================
        // 1. 拉取代码
        // ============================================================
        stage('① 拉取代码') {
            steps {
                checkout scm
                sh 'git log --oneline -3'
            }
        }

        // ============================================================
        // 2. 运行测试
        // ============================================================
        stage('② 运行测试') {
            when { expression { params.RUN_TESTS == 'yes' } }
            steps {
                dir('backend') {
                    sh 'pip install -r requirements.txt'
                }
                dir('backend/auto_test') {
                    sh '''
                        cat > config/test_env.yaml << 'EOF'
default_env: dev
dev:
  base_url: http://127.0.0.1:8000/api
  admin:
    username: admin
    password: "123456"
EOF
                        cd ..
                        nohup python main.py > server.log 2>&1 &
                        for i in $(seq 1 30); do
                            if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
                                echo "后端就绪"; break
                            fi
                            sleep 1
                        done
                        cd auto_test
                        pytest -v --junitxml=./junit-report.xml
                    '''
                }
            }
            post {
                always {
                    junit(testResults: 'backend/auto_test/junit-report.xml')
                    sh 'pkill -f "main:app" || true'
                }
            }
        }

        // ============================================================
        // 3. 构建 Docker 镜像
        // ============================================================
        stage('③ 构建镜像') {
            steps {
                script {
                    echo "构建后端镜像..."
                    sh """
                        docker build -f backend/Dockerfile.backend \
                            -t ${IMAGE_BACKEND}:${IMAGE_TAG} \
                            -t ${IMAGE_BACKEND}:latest \
                            backend/
                    """

                    echo "构建前端镜像..."
                    sh """
                        docker build -f web/Dockerfile.frontend \
                            -t ${IMAGE_FRONTEND}:${IMAGE_TAG} \
                            -t ${IMAGE_FRONTEND}:latest \
                            web/
                    """
                }
            }
        }

        // ============================================================
        // 4. 推送镜像到阿里云
        // ============================================================
        stage('④ 推送镜像') {
            steps {
                script {
                    // 登录阿里云镜像仓库
                    // 需要在 Jenkins 配置凭证：阿里云账号 + 镜像仓库密码
                    withDockerRegistry([
                        credentialsId: 'aliyun-docker-registry',
                        url: "https://${REGISTRY}"
                    ]) {
                        sh """
                            docker push ${IMAGE_BACKEND}:${IMAGE_TAG}
                            docker push ${IMAGE_BACKEND}:latest
                            docker push ${IMAGE_FRONTEND}:${IMAGE_TAG}
                            docker push ${IMAGE_FRONTEND}:latest
                        """
                    }
                }
            }
        }

        // ============================================================
        // 5. 登录正式服务器 → 拉取新镜像 → 重启服务
        // ============================================================
        stage('⑤ 部署') {
            steps {
                sshagent(credentials: ['deploy-server-ssh']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_HOST} '
                            set -e
                            echo "===== 登录镜像仓库 ====="
                            # 这里要用 docker login，密码在正式服上提前登录过就不用再登
                            # 确保正式服已经 docker login 过了
                            # docker login ${REGISTRY} -u xxx -p xxx

                            cd ${DEPLOY_PATH}

                            echo "===== 拉取最新代码（docker-compose.prod.yml）====="
                            git pull origin ${BRANCH}

                            echo "===== 拉取最新镜像 ====="
                            cd deploy
                            docker compose -f docker-compose.prod.yml pull fastapi frontend

                            echo "===== 重启服务 ====="
                            docker compose -f docker-compose.prod.yml up -d

                            echo "===== 清理旧镜像 ====="
                            docker image prune -f --filter "dangling=true" || true

                            echo "===== 部署完成 ====="
                        '
                    """
                }
            }
        }

        // ============================================================
        // 6. 健康检查
        // ============================================================
        stage('⑥ 验证') {
            steps {
                sshagent(credentials: ['deploy-server-ssh']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_HOST} '
                            echo "等待服务就绪..."
                            for i in \$(seq 1 12); do
                                code=\$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
                                if [ "\$code" = "200" ]; then
                                    echo "✅ 服务正常"
                                    docker compose -f ${DEPLOY_PATH}/deploy/docker-compose.prod.yml ps
                                    exit 0
                                fi
                                sleep 5
                            done
                            echo "❌ 服务异常"
                            exit 1
                        '
                    """
                }
            }
        }
    }

    post {
        success {
            echo "✅ 构建 #${BUILD_NUMBER} 部署成功！"
        }
        failure {
            echo "❌ 构建 #${BUILD_NUMBER} 失败，请检查日志"
        }
    }
}
