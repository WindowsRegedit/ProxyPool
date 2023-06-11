cd proxypool\processors\static
Remove-Item css -Force -Recurse
Remove-Item js -Force -Recurse
mkdir css
mkdir js
Invoke-WebRequest -Uri https://unpkg.com/element-plus/dist/index.css -Outfile css\element-plus.css
Invoke-WebRequest -Uri https://unpkg.com/vue/dist/vue.global.prod.js -Outfile js\vue.prod.js
Invoke-WebRequest -Uri https://unpkg.com/element-plus/dist/index.full.min.js -Outfile js\element-plus.full.min.js
Invoke-WebRequest -Uri https://unpkg.com/bootstrap/dist/css/bootstrap.min.css -Outfile css\bootstrap.min.css
Invoke-WebRequest -Uri https://unpkg.com/bootstrap/dist/js/bootstrap.bundle.min.js -Outfile js\bootstrap.bundle.min.js
Invoke-WebRequest -Uri https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css -Outfile css\swagger-ui.css
Invoke-WebRequest -Uri https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js -Outfile js\swagger-ui-bundle.js
Invoke-WebRequest -Uri https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-standalone-preset.js -Outfile js\swagger-ui-standalone-preset.js
cd ..\..\..