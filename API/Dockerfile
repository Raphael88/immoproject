
# Étape 1 : Utiliser une image Python légère
FROM python:3.11-slim

# Pour éviter les erreurs debconf (non-interactif)
ENV DEBIAN_FRONTEND=noninteractive

# Étape 2 : Installer les dépendances système + le driver ODBC
RUN apt-get update && \
    apt-get install -y curl gnupg apt-transport-https gcc g++ && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    apt-get install -y unixodbc-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Étape 3 : Définir le dossier de travail
WORKDIR /app


COPY requirements.txt /app/

# Étape 5 : Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Étape 4 : Copier le code dans le conteneur
COPY . /app

# Forçage du port
EXPOSE 8000

# Étape 6 : Lancer le serveur avec gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "API_immoproject:app"]