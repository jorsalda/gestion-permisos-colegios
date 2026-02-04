from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Docente, Permiso, Colegio, Usuario
import config
from datetime import datetime, timedelta

# Crear la app
app = Flask(__name__)
app.config.from_object(config.Config)

# Inicializar base de datos
db.init_app(app)

# 🔐 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# 🏠 Ruta principal
@app.route('/')
def index():
    return redirect(url_for('formulario'))

# 🔑 Registro - CON 15 DÍAS DE ACCESO INMEDIATO
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        colegio_nombre = request.form['colegio'].strip()

        if not email or not password or not colegio_nombre:
            flash("❌ Todos los campos son obligatorios", "danger")
            return render_template('register.html')

        colegio = Colegio.query.filter_by(nombre=colegio_nombre).first()
        if not colegio:
            colegio = Colegio(nombre=colegio_nombre)
            db.session.add(colegio)
            db.session.commit()

        if Usuario.query.filter_by(email=email).first():
            flash("❌ Este correo ya está registrado", "danger")
            return render_template('register.html')

        # ✅ CREAR USUARIO CON 15 DÍAS DE ACCESO INMEDIATO
        fecha_registro = datetime.utcnow()
        usuario = Usuario(
            email=email,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
            colegio_id=colegio.id,
            fecha_registro=fecha_registro,
            estatus='temporal',
            fecha_limite_prueba=fecha_registro + timedelta(days=15),
            aprobado_permanentemente=False
        )
        db.session.add(usuario)
        db.session.commit()

        # ✅ AVISO EN CONSOLA
        print("\n" + "=" * 60)
        print("⚠️ ¡NUEVO REGISTRO DE USUARIO!")
        print("=" * 60)
        print(f"📧 Email: {email}")
        print(f"🏫 Colegio: {colegio_nombre}")
        print(f"📅 Registrado: {fecha_registro.strftime('%Y-%m-%d %H:%M')}")
        print(f"⏳ Acceso hasta: {(fecha_registro + timedelta(days=15)).strftime('%Y-%m-%d')}")
        print(f"🔗 Administrar en: http://localhost:5000/admin/solicitudes")
        print("=" * 60 + "\n")

        flash("✅ Registro exitoso. Tienes 15 días de acceso gratuito.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# 🔑 Login - CON VERIFICACIÓN DE ACCESO
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            # Verificar si tiene acceso
            if not usuario.tiene_acceso():
                if usuario.estatus == 'bloqueado':
                    flash("❌ Tu cuenta está bloqueada", "danger")
                elif usuario.estatus == 'pendiente_aprobacion':
                    flash("❌ Tu período de 15 días terminó. Espera la aprobación del administrador.", "danger")
                else:
                    flash("❌ No tienes acceso al sistema", "danger")
                return render_template('login.html')

            # Si es temporal, mostrar días restantes
            if usuario.estatus == 'temporal' and not usuario.aprobado_permanentemente:
                dias_restantes = usuario.dias_restantes_prueba()
                flash(f"✅ Acceso temporal - Días restantes: {dias_restantes}", "info")

            login_user(usuario)
            return redirect(url_for('formulario'))

        flash("❌ Email o contraseña incorrectos", "danger")

    return render_template('login.html')

# 🚪 Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 📝 Formulario - CON VERIFICACIÓN DE ACCESO
@app.route('/formulario', methods=['GET', 'POST'])
@login_required
def formulario():
    # Verificar si el usuario tiene acceso
    if not current_user.tiene_acceso():
        if current_user.estatus == 'pendiente_aprobacion':
            flash("❌ Tu período de 15 días terminó. Espera la aprobación del administrador.", "danger")
        elif current_user.estatus == 'bloqueado':
            flash("❌ Tu cuenta está bloqueada", "danger")
        return redirect(url_for('login'))

    # Si es temporal, mostrar días restantes
    if current_user.estatus == 'temporal' and not current_user.aprobado_permanentemente:
        dias_restantes = current_user.dias_restantes_prueba()
        flash(f"⚠️ Acceso temporal - Días restantes: {dias_restantes}", "warning")

    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    tipos = ['Vacaciones', 'Enfermedad', 'Permiso Personal', 'Capacitación', 'Otro']

    # Verificar si se está viendo historial
    docente_seleccionado = None
    historial = []

    if request.method == 'POST':
        if 'ver_historial' in request.form:
            docente_id = request.form['docente']
            docente_seleccionado = Docente.query.get(docente_id)
            if docente_seleccionado:
                historial = Permiso.query.filter_by(
                    docente_id=docente_id,

                ).order_by(Permiso.fecha_inicio.desc()).all()
        elif 'guardar' in request.form:
            docente_id = request.form['docente']
            nuevo_permiso = Permiso(
                docente_id=docente_id,
                fecha_inicio=request.form['fecha_inicio'],
                fecha_fin=request.form['fecha_fin'],
                tipo=request.form['tipo'],
                observacion=request.form.get('observacion', ''),
                colegio_id=current_user.colegio_id  # ← Asegúrate que esto no sea None
            )
            db.session.add(nuevo_permiso)
            db.session.commit()
            flash("✅ Permiso guardado", "success")
            return redirect(url_for('listado'))

    return render_template('formulario.html',
                           docentes=docentes,
                           tipos=tipos,
                           docente_seleccionado=docente_seleccionado,
                           historial=historial)

# 👥 Docentes
@app.route('/docentes')
@login_required
def listar_docentes():
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    return render_template('docentes.html', docentes=docentes)

@app.route('/docente/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_docente():
    if request.method == 'POST':
        nombre = request.form['nombre']
        if nombre:
            nuevo = Docente(nombre=nombre, colegio_id=current_user.colegio_id)
            db.session.add(nuevo)
            db.session.commit()
            flash("✅ Docente agregado correctamente", "success")
            return redirect(url_for('listar_docentes'))
        else:
            flash("❌ El nombre no puede estar vacío", "danger")

    return render_template('docente_form.html', docente=None)

@app.route('/docente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_docente(id):
    docente = Docente.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()

    if request.method == 'POST':
        docente.nombre = request.form['nombre']
        db.session.commit()
        flash("✅ Docente editado correctamente", "success")
        return redirect(url_for('listar_docentes'))

    return render_template('docente_form.html', docente=docente)

@app.route('/docente/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_docente(id):
    docente = Docente.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()

    if Permiso.query.filter_by(docente_id=id, colegio_id=current_user.colegio_id).first():
        flash("⚠️ No se puede eliminar: el docente tiene permisos registrados.", "warning")
    else:
        db.session.delete(docente)
        db.session.commit()
        flash("🗑️ Docente eliminado correctamente", "success")

    return redirect(url_for('listar_docentes'))

# 📋 Listado de permisos
@app.route('/listado')
@login_required
def listado():
    # OPCIÓN 1: Mostrar permisos de los docentes del colegio (RECOMENDADO)
    # Obtener IDs de docentes del colegio del usuario
    docentes_del_colegio = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    docentes_ids = [d.id for d in docentes_del_colegio]

    # Buscar permisos de esos docentes
    permisos = Permiso.query.filter(Permiso.docente_id.in_(docentes_ids)).order_by(Permiso.fecha_inicio.desc()).all()

    # Para debug: ver qué está pasando
    print(f"DEBUG: Colegio ID: {current_user.colegio_id}")
    print(f"DEBUG: Docentes del colegio: {docentes_ids}")
    print(f"DEBUG: Permisos encontrados: {len(permisos)}")

    return render_template('permisos.html', permisos=permisos)


# ✏️ Editar permiso
@app.route('/permiso/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_permiso(id):
    permiso = Permiso.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    tipos = ['Vacaciones', 'Enfermedad', 'Permiso Personal', 'Capacitación', 'Otro']

    if request.method == 'POST':
        permiso.docente_id = request.form['docente']
        permiso.fecha_inicio = request.form['fecha_inicio']
        permiso.fecha_fin = request.form['fecha_fin']
        permiso.tipo = request.form['tipo']
        permiso.observacion = request.form.get('observacion', '')

        db.session.commit()
        flash("✅ Permiso actualizado correctamente", "success")
        return redirect(url_for('listado'))

    return render_template('permiso_form.html', permiso=permiso, docentes=docentes, tipos=tipos)

# 🗑️ Eliminar permiso
@app.route('/permiso/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_permiso(id):
    permiso = Permiso.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()

    db.session.delete(permiso)
    db.session.commit()
    flash("🗑️ Permiso eliminado correctamente", "success")

    return redirect(url_for('listado'))

# 👮‍♂️ Administración - PANEL DE SOLICITUDES
@app.route('/admin/solicitudes')
@login_required
def solicitudes():
    # Solo tú (jorsalda@gmail.com) puede acceder
    if current_user.email != 'jorsalda@gmail.com':
        abort(403)

    # Obtener todos los usuarios (excepto administradores)
    usuarios = Usuario.query.filter(Usuario.email != 'jorsalda@gmail.com').order_by(Usuario.fecha_registro.desc()).all()

    return render_template('solicitudes.html',
                           usuarios=usuarios,
                           now=datetime.utcnow(),
                           timedelta=timedelta)

# 👮‍♂️ APROBAR USUARIO PERMANENTEMENTE
@app.route('/admin/aprobar/<int:id>')
@login_required
def aprobar_usuario(id):
    if current_user.email != 'jorsalda@gmail.com':
        abort(403)

    usuario = Usuario.query.get_or_404(id)

    # Aprobar permanentemente
    usuario.aprobado_permanentemente = True
    usuario.estatus = 'activo'
    db.session.commit()

    print("\n" + "=" * 60)
    print("✅ ¡USUARIO APROBADO PERMANENTEMENTE!")
    print("=" * 60)
    print(f"📧 Usuario: {usuario.email}")
    print(f"🏫 Colegio: {usuario.colegio.nombre}")
    print(f"✅ Aprobado permanentemente")
    print(f"📅 Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60 + "\n")

    flash(f"✅ Usuario {usuario.email} aprobado permanentemente", "success")
    return redirect(url_for('solicitudes'))

# 👮‍♂️ RECHAZAR USUARIO (BLOQUEAR)
@app.route('/admin/rechazar/<int:id>')
@login_required
def rechazar_usuario(id):
    if current_user.email != 'jorsalda@gmail.com':
        abort(403)

    usuario = Usuario.query.get_or_404(id)

    # Bloquear usuario
    usuario.estatus = 'bloqueado'
    db.session.commit()

    print("\n" + "=" * 60)
    print("❌ ¡USUARIO BLOQUEADO!")
    print("=" * 60)
    print(f"📧 Usuario: {usuario.email}")
    print(f"🏫 Colegio: {usuario.colegio.nombre}")
    print(f"❌ Bloqueado permanentemente")
    print(f"📅 Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60 + "\n")

    flash(f"❌ Usuario {usuario.email} bloqueado", "danger")
    return redirect(url_for('solicitudes'))
# En la consola de Flask o en una ruta temporal:
@app.route('/debug')
@login_required
def debug():
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    return f"""
    Usuario: {current_user.email}<br>
    Colegio ID: {current_user.colegio_id}<br>
    Colegio: {current_user.colegio.nombre if current_user.colegio else 'None'}<br>
    Docentes en colegio: {len(docentes)}<br>
    Docentes: {[d.nombre for d in docentes]}<br>
    Tiene acceso: {current_user.tiene_acceso()}
    """
# 🧪 Crear tablas
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)



