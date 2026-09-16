@echo off
setlocal
set MAVEN_VERSION=3.9.11
set SCRIPT_DIR=%~dp0
set MAVEN_DIR=%SCRIPT_DIR%.mvn\wrapper\dists\apache-maven-%MAVEN_VERSION%
set MAVEN_BIN=%MAVEN_DIR%\bin\mvn.cmd

if not exist "%MAVEN_BIN%" (
    if not exist "%SCRIPT_DIR%.mvn\wrapper\dists" mkdir "%SCRIPT_DIR%.mvn\wrapper\dists"
    powershell -NoProfile -Command "$url='https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/%MAVEN_VERSION%/apache-maven-%MAVEN_VERSION%-bin.zip'; $zip='%TEMP%\apache-maven-%MAVEN_VERSION%.zip'; Invoke-WebRequest -Uri $url -OutFile $zip; Expand-Archive -Path $zip -DestinationPath '%SCRIPT_DIR%.mvn\wrapper\dists' -Force; Remove-Item $zip"
)

call "%MAVEN_BIN%" %*
