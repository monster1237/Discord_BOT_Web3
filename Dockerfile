# 使用官方Python作为基础镜像
FROM python:3.8-slim

# 更新软件包列表并安装必要软件
RUN apt-get update && \
    apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip

# 添加Chrome源
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'

# 更新软件包列表并安装必要软件
RUN apt-get update && \
    apt-get install -y \
    google-chrome-stable

# 安装Chromedriver
RUN LATEST_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -O /tmp/chromedriver.zip "http://chromedriver.storage.googleapis.com/${LATEST_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# 安装GeckoDriver
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.29.0/geckodriver-v0.29.0-linux64.tar.gz" && \
    tar -xzf geckodriver-v0.29.0-linux64.tar.gz && \
    chmod +x geckodriver && \
    mv geckodriver /usr/local/bin/

# 设置工作目录
WORKDIR /usr/src/app

# 复制项目文件
COPY . .

# 安装项目依赖
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 8080

CMD ["python", "main.py"]
