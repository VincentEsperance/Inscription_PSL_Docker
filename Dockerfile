FROM public.ecr.aws/lambda/python:3.10

# Install system dependencies
RUN yum install -y \
    unzip \
    wget \
    curl \
    xorg-x11-fonts-Type1 \
    xorg-x11-fonts-75dpi \
    xorg-x11-fonts-100dpi \
    xorg-x11-utils \
    xorg-x11-fonts-cyrillic \
    atk \
    cups-libs \
    gtk3 \
    libXcomposite \
    alsa-lib \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    libXss \
    libX11 \
    GConf2 \
    && yum clean all

# Install Chrome for Testing (CfT) + ChromeDriver (same version)
RUN CFT_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) \
    && wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CFT_VERSION/linux64/chrome-linux64.zip \
    && wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CFT_VERSION/linux64/chromedriver-linux64.zip \
    && unzip chrome-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chrome-linux64 /opt/chrome \
    && mv chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm -rf chrome-linux64.zip chromedriver-linux64.zip chromedriver-linux64

ENV PATH="/opt/chrome:$PATH"

# Install Selenium
RUN pip install selenium==4.18.1

# Copy Lambda handler
COPY app.py ${LAMBDA_TASK_ROOT}

CMD ["app.handler"]
