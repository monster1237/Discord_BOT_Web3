# 基础镜像
FROM python:3.8-slim-buster

# 设置工作目录
WORKDIR /usr/src/app

# 添加 Chrome 的源
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list'

# 更新软件包列表并安装指定版本的 Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable=114.0.0.0

# 获取指定版本的 ChromeDriver
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/114.0.0.0/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 暴露端口（如果需要）
EXPOSE 8000

# 运行应用
CMD ["python", "main.py"]
