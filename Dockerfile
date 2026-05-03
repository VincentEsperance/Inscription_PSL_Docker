# Image de base AWS Lambda Python 3.12
# Python 3.14 n'est pas encore disponible en image Lambda officielle,
# la version 3.12 est la plus récente disponible (comportement identique).
FROM public.ecr.aws/lambda/python:3.12

# Dépendances système nécessaires à Chromium / Playwright
RUN dnf install -y \
    atk \
    cups-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi \
    xorg-x11-fonts-cyrillic \
    xorg-x11-fonts-misc \
    xorg-x11-fonts-Type1 \
    xorg-x11-utils \
    alsa-lib \
    libdrm \
    mesa-libgbm \
    nss \
    nspr \
    && dnf clean all

# Installation de Playwright et ses dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation du navigateur Chromium via Playwright
RUN PLAYWRIGHT_BROWSERS_PATH=/ms-playwright python -m playwright install chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Copie du code
COPY handler.py ${LAMBDA_TASK_ROOT}/

# Point d'entrée Lambda
CMD ["handler.lambda_handler"]
