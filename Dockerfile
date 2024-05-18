# 基础镜像
FROM python:3.8-slim-buster

# 设置工作目录
WORKDIR /usr/src/app

# 安装必要的软件包
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libappindicator3-1 \
    libindicator7 \
    fonts-liberation \
    libasound2 \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 添加 Google Chrome 的源，并安装 Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list' && \
    apt-get update && \
    apt-get install -y google-chrome-stable
    
# 下载特定版本的 ChromeDriver
ARG CHROMEDRIVER_VERSION=125.0.6422.60
RUN wget -O chromedriver_linux64.zip https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口（如果需要）
EXPOSE 8000

# 设置环境变量
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 运行应用
CMD ["python", "main.py"]
