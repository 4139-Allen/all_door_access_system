// ============================================================
// 门禁管理系统 - Jenkins CI/CD Pipeline（单机版）
// workspace 跑测试（8001端口） → /opt/myproject/ 部署
// ============================================================

pipeline {
    agent any

    environment {
        PROJECT_DIR = '/opt/myproject/all_door_access_system'
    }

    parameters {
        choice(name: 'RUN_TESTS', choices: ['yes', 'no'], description: '部署前跑测试？')
    }

    triggers {
        githubPush()
    }

    stages {
        // ============================================================
        // 1. 拉取代码到 workspace（跑测试用）
        // ============================================================
        stage('① 拉取代码') {
            steps {
                checkout scm
                sh 'git log --oneline -3'
            }
        }

        // ============================================================
        // 2. 运行测试（用 workspace 的代码，端口 8001）
        // ============================================================
        stage('② 运行测试') {
            when { expression { params.RUN_TESTS == 'yes' } }
            steps {
                dir('backend') {
                    sh 'pip install -r requirements.txt && pip install allure-pytest'
                }
                dir('backend/auto_test') {
                    sh '''
                        cat > ../.env << 'EOF'
SECRET_KEY=test-secret-key-for-ci
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DB=door_access_test
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
EOF
                        cat > config/test_env.yaml << 'EOF'
default_env: dev
dev:
  base_url: http://127.0.0.1:8001/api
  admin:
    username: admin
    password: "123456"
EOF
                        cd ..
                        echo "迁移测试数据库（先 stamp 跳过旧迁移）..."
                        python3 -c "
from alembic.config import Config
from alembic import command
cfg = Config('database/migrations/alembic.ini')
command.stamp(cfg, '12c2f4507704')
" && python3 database/migrations/manage_db.py upgrade
                        echo "清理旧进程，启动测试后端（端口 8001）..."
                        pkill -f "uvicorn main:app" || true
                        nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 > server.log 2>&1 &
                        for i in $(seq 1 30); do
                            if curl -s http://127.0.0.1:8001/api/health > /dev/null 2>&1; then
                                echo "后端就绪"; break
                            fi
                            sleep 1
                        done
                        echo "===== 验证测试环境 ====="
                        echo "确认数据库配置:"
                        python3 -c "from core.config import MYSQL_DB; print(f'数据库: {MYSQL_DB}')"
                        python3 -c "
import pymysql
db = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='123456', database='door_access_test')
db.close()
print('door_access_test 连接成功')
" && echo "数据库验证通过" || (echo "数据库验证失败！测试终止" && exit 1)
                        echo "========================="
                        echo "开始测试..."
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
                    allure([
                        includeProperties: false,
                        results: [[path: 'backend/auto_test/report']]
                    ])
                    sh 'pkill -f "main:app" || true'
                }
            }
        }

        // ============================================================
        // 3. 部署：项目目录 git pull -> docker compose
        // ============================================================
        stage('③ 部署') {
            steps {
                dir(PROJECT_DIR) {
                    sh '''
                        echo "拉取最新代码..."
                        git pull origin main

                        echo "构建并重启服务..."
                        cd deploy
                        docker compose up -d --build

                        echo "迁移生产数据库（先 stamp 跳过旧迁移）..."
                        docker compose exec -T fastapi python -c "
from alembic.config import Config
from alembic import command
cfg = Config('database/migrations/alembic.ini')
command.stamp(cfg, '12c2f4507704')
" && docker compose exec -T fastapi python database/migrations/manage_db.py upgrade

                        echo "部署完成"
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
                            echo "服务正常"
                            exit 0
                        fi
                        sleep 5
                    done
                    echo "服务异常"
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "构建 #${BUILD_NUMBER} 部署成功！"
        }
        failure {
            echo "构建 #${BUILD_NUMBER} 失败，请检查日志"
        }
    }
}
