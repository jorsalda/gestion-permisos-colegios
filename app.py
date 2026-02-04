from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Docente, Permiso, Colegio, Usuario
import config
from datetime import datetime, timedelta

# ============ CONFIGURACIÓN ============
app = Flask(__name__)
app.config.from_object(config.Config)
db.init_app(app)

# ============ AUTENTICACIÓN ============
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


# ============ RUTAS PÚBLICAS ============
@app.route('/')
def index():
    return redirect(url_for('formulario'))


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

        fecha_registro = datetime.utcnow()
        usuario = Usuario(
            email=email,
            password_hash=generate_password_hash(password),
            colegio_id=colegio.id,
            fecha_registro=fecha_registro,
            estatus='temporal',
            fecha_limite_prueba=fecha_registro + timedelta(days=15),
            aprobado_permanentemente=False
        )
        db.session.add(usuario)
        db.session.commit()

        flash("✅ Registro exitoso. Tienes 15 días de acceso.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            if not usuario.tiene_acceso():
                flash("❌ No tienes acceso al sistema", "danger")
                return render_template('login.html')

            login_user(usuario)
            return redirect(url_for('formulario'))

        flash("❌ Credenciales incorrectas", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ============ CRUD DOCENTES ============
@app.route('/docentes')
@login_required
def listar_docentes():
    """Listar todos los docentes del colegio"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    return render_template('docentes.html', docentes=docentes)


@app.route('/docente/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_docente():
    """Crear nuevo docente"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if nombre:
            docente = Docente(
                nombre=nombre,
                colegio_id=current_user.colegio_id
            )
            db.session.add(docente)
            db.session.commit()
            flash("✅ Docente agregado correctamente", "success")
            return redirect(url_for('listar_docentes'))
        else:
            flash("❌ El nombre no puede estar vacío", "danger")

    return render_template('docente_form.html', docente=None)


@app.route('/docente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_docente(id):
    """Editar docente existente"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    docente = Docente.query.filter_by(
        id=id,
        colegio_id=current_user.colegio_id
    ).first_or_404()

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if nombre:
            docente.nombre = nombre
            db.session.commit()
            flash("✅ Docente editado correctamente", "success")
            return redirect(url_for('listar_docentes'))
        else:
            flash("❌ El nombre no puede estar vacío", "danger")

    return render_template('docente_form.html', docente=docente)


@app.route('/docente/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_docente(id):
    """Eliminar docente (si no tiene permisos)"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    docente = Docente.query.filter_by(
        id=id,
        colegio_id=current_user.colegio_id
    ).first_or_404()

    # Verificar si tiene permisos asociados
    tiene_permisos = Permiso.query.filter_by(
        docente_id=id,
        colegio_id=current_user.colegio_id
    ).first()

    if tiene_permisos:
        flash("⚠️ No se puede eliminar: el docente tiene permisos registrados", "warning")
    else:
        db.session.delete(docente)
        db.session.commit()
        flash("🗑️ Docente eliminado correctamente", "success")

    return redirect(url_for('listar_docentes'))


# ============ CRUD PERMISOS ============
@app.route('/formulario', methods=['GET', 'POST'])
@login_required
def formulario():
    """Formulario principal para crear permisos y ver historial"""
    if not current_user.tiene_acceso():
        flash("❌ Acceso denegado", "danger")
        return redirect(url_for('login'))

    # Obtener docentes del colegio actual
    docentes = Docente.query.filter_by(
        colegio_id=current_user.colegio_id
    ).order_by(Docente.nombre).all()

    # Tipos de permisos
    tipos = ['Vacaciones', 'Enfermedad', 'Permiso Personal', 'Capacitación', 'Otro']

    docente_seleccionado = None
    historial = []

    if request.method == 'POST':
        # 🔍 VER HISTORIAL DE DOCENTE
        if 'ver_historial' in request.form:
            docente_id = request.form['docente']
            if docente_id:
                docente_seleccionado = Docente.query.filter_by(
                    id=docente_id,
                    colegio_id=current_user.colegio_id
                ).first()

                if docente_seleccionado:
                    historial = Permiso.query.filter_by(
                        docente_id=docente_id,
                        colegio_id=current_user.colegio_id
                    ).order_by(Permiso.fecha_inicio.desc()).all()
                else:
                    flash("❌ Docente no encontrado", "danger")

        # 💾 CREAR NUEVO PERMISO
        elif 'guardar' in request.form:
            docente_id = request.form['docente']
            fecha_inicio = request.form['fecha_inicio']
            fecha_fin = request.form['fecha_fin']
            tipo = request.form['tipo']
            observacion = request.form.get('observacion', '').strip()

            # Validaciones
            if not docente_id or not fecha_inicio or not fecha_fin or not tipo:
                flash("❌ Faltan campos obligatorios", "danger")
                return redirect(url_for('formulario'))

            # Verificar que el docente pertenezca al colegio
            docente = Docente.query.filter_by(
                id=docente_id,
                colegio_id=current_user.colegio_id
            ).first()

            if not docente:
                flash("❌ Docente no válido", "danger")
                return redirect(url_for('formulario'))

            try:
                # Convertir fechas
                fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

                # Validar que fecha fin sea mayor o igual a fecha inicio
                if fecha_fin_dt < fecha_inicio_dt:
                    flash("❌ La fecha fin no puede ser anterior a la fecha inicio", "danger")
                    return redirect(url_for('formulario'))

                # Crear permiso
                nuevo_permiso = Permiso(
                    docente_id=docente_id,
                    fecha_inicio=fecha_inicio_dt,
                    fecha_fin=fecha_fin_dt,
                    tipo=tipo,
                    observacion=observacion,
                    colegio_id=current_user.colegio_id,
                    aprobado_por=current_user.id
                )

                db.session.add(nuevo_permiso)
                db.session.commit()
                flash("✅ Permiso creado correctamente", "success")
                return redirect(url_for('listado'))

            except ValueError:
                flash("❌ Formato de fecha incorrecto (use YYYY-MM-DD)", "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"❌ Error al guardar: {str(e)}", "danger")

    return render_template(
        'formulario.html',
        docentes=docentes,
        tipos=tipos,
        docente_seleccionado=docente_seleccionado,
        historial=historial
    )


@app.route('/listado')
@login_required
def listado():
    """Listar todos los permisos del colegio"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    # Obtener IDs de docentes del colegio
    docentes_ids = [
        d.id for d in Docente.query.filter_by(
            colegio_id=current_user.colegio_id
        ).all()
    ]

    # Obtener permisos de esos docentes
    permisos = Permiso.query.filter(
        Permiso.docente_id.in_(docentes_ids)
    ).order_by(Permiso.fecha_inicio.desc()).all()

    # Obtener colegio para mostrar nombre
    colegio = Colegio.query.get(current_user.colegio_id)

    return render_template(
        'permisos.html',
        permisos=permisos,
        colegio=colegio
    )


@app.route('/permiso/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_permiso(id):
    """Editar permiso existente"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    # Buscar permiso (debe pertenecer al colegio del usuario)
    permiso = Permiso.query.filter_by(
        id=id,
        colegio_id=current_user.colegio_id
    ).first_or_404()

    # Obtener docentes y tipos para el formulario
    docentes = Docente.query.filter_by(
        colegio_id=current_user.colegio_id
    ).order_by(Docente.nombre).all()

    tipos = ['Vacaciones', 'Enfermedad', 'Permiso Personal', 'Capacitación', 'Otro']

    if request.method == 'POST':
        # Validar campos
        docente_id = request.form['docente']
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']
        tipo = request.form['tipo']
        observacion = request.form.get('observacion', '').strip()

        if not docente_id or not fecha_inicio or not fecha_fin or not tipo:
            flash("❌ Faltan campos obligatorios", "danger")
            return redirect(url_for('editar_permiso', id=id))

        # Verificar que el docente pertenezca al colegio
        docente = Docente.query.filter_by(
            id=docente_id,
            colegio_id=current_user.colegio_id
        ).first()

        if not docente:
            flash("❌ Docente no válido", "danger")
            return redirect(url_for('editar_permiso', id=id))

        try:
            # Convertir fechas
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

            # Validar fechas
            if fecha_fin_dt < fecha_inicio_dt:
                flash("❌ La fecha fin no puede ser anterior a la fecha inicio", "danger")
                return redirect(url_for('editar_permiso', id=id))

            # Actualizar permiso
            permiso.docente_id = docente_id
            permiso.fecha_inicio = fecha_inicio_dt
            permiso.fecha_fin = fecha_fin_dt
            permiso.tipo = tipo
            permiso.observacion = observacion
            permiso.aprobado_por = current_user.id  # Actualizar quien aprueba

            db.session.commit()
            flash("✅ Permiso actualizado correctamente", "success")
            return redirect(url_for('listado'))

        except ValueError:
            flash("❌ Formato de fecha incorrecto (use YYYY-MM-DD)", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar: {str(e)}", "danger")

    return render_template(
        'permiso_form.html',
        permiso=permiso,
        docentes=docentes,
        tipos=tipos
    )


@app.route('/permiso/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_permiso(id):
    """Eliminar permiso"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    # Buscar permiso (debe pertenecer al colegio del usuario)
    permiso = Permiso.query.filter_by(
        id=id,
        colegio_id=current_user.colegio_id
    ).first_or_404()

    try:
        db.session.delete(permiso)
        db.session.commit()
        flash("🗑️ Permiso eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar: {str(e)}", "danger")

    return redirect(url_for('listado'))


# ============ VISTA DETALLE DE PERMISO ============
@app.route('/permiso/<int:id>')
@login_required
def ver_permiso(id):
    """Ver detalles de un permiso específico"""
    if not current_user.tiene_acceso():
        flash("❌ No tienes acceso", "danger")
        return redirect(url_for('login'))

    permiso = Permiso.query.filter_by(
        id=id,
        colegio_id=current_user.colegio_id
    ).first_or_404()

    return render_template('permiso_detalle.html', permiso=permiso)


# ============ ADMINISTRACIÓN ============
@app.route('/admin/solicitudes')
@login_required
def solicitudes():
    """Panel de administración de usuarios"""
    if current_user.email != 'jorsalda@gmail.com':
        abort(403)

    usuarios = Usuario.query.filter(
        Usuario.email != 'jorsalda@gmail.com'
    ).order_by(Usuario.fecha_registro.desc()).all()

    return render_template(
        'solicitudes.html',
        usuarios=usuarios,
        now=datetime.utcnow(),
        timedelta=timedelta
    )


@app.route('/admin/aprobar/<int:id>')
@login_required
def aprobar_usuario(id):
    """Aprobar usuario permanentemente"""
    if current_user.email != 'jorsalda@gmail.com':
        abort(403)

    usuario = Usuario.query.get_or_404(id)
    usuario.aprobado_permanentemente = True
    usuario.estatus = 'activo'
    db.session.commit()

    flash(f"✅ Usuario {usuario.email} aprobado permanentemente", "success")
    return redirect(url_for('solicitudes'))


@app.route('/admin/rechazar/<int:id>')
@login_required
def rechazar_usuario(id):
    """Bloquear usuario"""
    if current_user.email != 'jorsalda@gmail.com':
        abort(403)

    usuario = Usuario.query.get_or_404(id)
    usuario.estatus = 'bloqueado'
    db.session.commit()

    flash(f"❌ Usuario {usuario.email} bloqueado", "danger")
    return redirect(url_for('solicitudes'))


# ============ UTILIDADES ============
@app.route('/debug')
@login_required
def debug():
    """Página de depuración"""
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    permisos_count = Permiso.query.filter_by(colegio_id=current_user.colegio_id).count()

    return f"""
    <h3>Información de Depuración</h3>
    <p><strong>Usuario:</strong> {current_user.email}</p>
    <p><strong>Colegio ID:</strong> {current_user.colegio_id}</p>
    <p><strong>Colegio:</strong> {current_user.colegio.nombre if current_user.colegio else 'Ninguno'}</p>
    <p><strong>Docentes en colegio:</strong> {len(docentes)}</p>
    <p><strong>Permisos en colegio:</strong> {permisos_count}</p>
    <p><strong>Tiene acceso:</strong> {current_user.tiene_acceso()}</p>
    <p><strong>Estado:</strong> {current_user.estatus}</p>
    <p><strong>Aprobado permanentemente:</strong> {current_user.aprobado_permanentemente}</p>
    """


# ============ INICIALIZACIÓN ============
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)