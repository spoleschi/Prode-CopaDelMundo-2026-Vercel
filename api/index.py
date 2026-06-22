import os
import sys
from flask import Flask

# 1. TRUCO CLAVE: Forzamos a Python a incluir la carpeta 'api' en su buscador de módulos
dir_actual = os.path.dirname(os.path.abspath(__file__))
if dir_actual not in sys.path:
    sys.path.insert(0, dir_actual)

# 2. Creamos la app con las rutas de plantillas correctas
app = Flask(
    __name__,
    template_folder=os.path.join(dir_actual, 'templates'),
    static_folder=os.path.join(dir_actual, 'static')
)

# 3. Importamos las configuraciones y blueprints (ahora que el sys.path está arreglado)
from config import Config
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.admin_routes import admin_bp
from routes.prediction_routes import prediction_bp
from routes.group_routes import group_bp

# 4. Cargamos la configuración desde el objeto Config
app.config.from_object(Config)

# 5. Registramos los Blueprints directo en la app principal
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(group_bp)

# 6. Para correr en local (Vercel ignora esto, pero usa la variable 'app' global de arriba)
if __name__ == "__main__":
    app.run(debug=True)