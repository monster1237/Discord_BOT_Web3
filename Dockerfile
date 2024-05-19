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
    firefox-esr \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 下载指定版本的 geckodriver
RUN wget -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin && \
    rm /tmp/geckodriver.tar.gz

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口（如果需要）
EXPOSE 8000

RUN chmod +x /usr/local/bin/geckodriver

# 设置环境变量
ENV GECKODRIVER_PATH=/usr/local/bin/geckodriver

# 运行应用
CMD ["python", "main.py"]
