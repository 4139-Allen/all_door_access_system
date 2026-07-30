// ============================================================
// 门禁管理系统 - Jenkins CI/CD Pipeline
// 单机方案：Jenkins + 应用在同一服务器
// ============================================================

pipeline {
    agent any

    environment {
        BRANCH = 'main'
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
                    sh 'pip install --break-system-packages -r requirements.txt && pip install --break-system-packages allure-pytest'
                }
                dir('backend/auto_test') {
                    sh '''
                        # 创建测试环境配置
                        cat > ../.env << 'EOF'
SECRET_KEY=test-secret-key-for-ci
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=test123
MYSQL_DB=door_access_test
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
EOF

                        cat > config/test_env.yaml << 'EOF'
default_env: dev
dev:
  base_url: http://127.0.0.1:8000/api
  admin:
    username: admin
    password: "123456"
EOF
                        cd ..
                        nohup python3 main.py > server.log 2>&1 &
                        for i in $(seq 1 30); do
                            if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
                                echo "后端就绪"; break
                            fi
                            sleep 1
                        done
                        cd auto_test
                        python3 -m pytest -v --junitxml=./junit-report.xml
                    '''
                }
            }
            post {
                always {
                    script {
                        try {
                            junit(testResults: 'backend/auto_test/junit-report.xml')
                        } catch (Exception e) {
                            echo "测试报告未生成，跳过"
                        }
                    }
                    sh 'pkill -f "main:app" || true'
                }
            }
        }

        // ============================================================
        // 3. 构建并部署
        // ============================================================
        stage('③ 构建并部署') {
            steps {
                dir('deploy') {
                    sh '''
                        echo "===== 构建并重启服务 ====="
                        docker compose up -d --build

                        echo "===== 清理旧镜像 ====="
                        docker image prune -f --filter "dangling=true" || true

                        echo "===== 部署完成 ====="
                    '''
                }
            }
        }

        // ============================================================
        // 4. 健康检查
        // ============================================================
        stage('④ 验证') {
            steps {
                sh '''
                    echo "等待服务就绪..."
                    for i in $(seq 1 12); do
                        code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
                        if [ "$code" = "200" ]; then
                            echo "✅ 服务正常"
                            docker compose -f deploy/docker-compose.yml ps
                            exit 0
                        fi
                        sleep 5
                    done
                    echo "❌ 服务异常"
                    exit 1
                '''
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
