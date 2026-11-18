// RedKyber · Modelo de datos: adaptar tablas, campos y vistas desde la propia aplicación
// (rutas modelo, agregar_campo, crear_tabla, crear_vista y eliminar_vista de la API)
class RedkyberModelo {
  constructor(contenedor = "section") {
    this.zona = document.querySelector(contenedor);
  }

  async llamar(ruta, cuerpo) {
    const r = await fetch("api/superapi.php?ruta=" + ruta, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo)
    }).then(r => r.json());
    if (r.ok === false) throw new Error(r.error);
    return r;
  }

  async render(mensaje = "") {
    const { tablas, vistas } = await fetch("api/superapi.php?ruta=modelo").then(r => r.json());
    const opcionesTipo = '<option>TEXT</option><option>INTEGER</option><option>REAL</option>';
    this.zona.innerHTML = `
      <div class="barra"><div><small>ADAPTACIÓN DEL SISTEMA</small><h2>Modelo de datos</h2></div></div>
      <p class="ayuda">Aquí se agregan campos, tablas y vistas sin tocar el código. Los nombres admiten letras, números y guion bajo.</p>
      <div id="aviso">${mensaje}</div>
      <div class="rejilla-modelo">
        <form id="f-campo"><h3>Agregar un campo</h3>
          <label>Tabla<select name="tabla">${tablas.map(t => `<option>${escapar(t.tabla)}</option>`).join("")}</select></label>
          <label>Nombre del campo<input name="nombre" required pattern="[A-Za-z_][A-Za-z0-9_]*"></label>
          <label>Tipo<select name="tipo">${opcionesTipo}</select></label>
          <button type="submit">Agregar campo</button></form>
        <form id="f-tabla"><h3>Crear una tabla</h3>
          <label>Nombre de la tabla<input name="nombre" required pattern="[A-Za-z_][A-Za-z0-9_]*"></label>
          <label>Campos (uno por línea: nombre tipo)<textarea name="campos" rows="4" required placeholder="matricula TEXT&#10;horas_vuelo REAL"></textarea></label>
          <button type="submit">Crear tabla</button></form>
        <form id="f-vista"><h3>Crear una vista</h3>
          <label>Nombre de la vista<input name="nombre" required pattern="[A-Za-z_][A-Za-z0-9_]*"></label>
          <label>Consulta SELECT<textarea name="sql" rows="4" required placeholder="SELECT c.nombre, SUM(p.total) AS total FROM pedidos p JOIN clientes c ON c.identificador = p.cliente_id GROUP BY c.nombre"></textarea></label>
          <button type="submit">Crear vista</button></form>
      </div>
      <h3>Tablas</h3>
      <div class="tabla-contenedor"><table><thead><tr><th>Tabla</th><th>Campos</th></tr></thead><tbody>
        ${tablas.map(t => `<tr><td>${escapar(t.tabla)}</td><td>${t.columnas.map(c => escapar(c.name) + " <small>" + escapar(c.type || "") + (c.pk ? " · PK" : "") + "</small>").join(" · ")}</td></tr>`).join("")}
      </tbody></table></div>
      <h3>Vistas</h3>
      ${vistas.length ? `<div class="tabla-contenedor"><table><thead><tr><th>Vista</th><th>Definición</th><th></th></tr></thead><tbody>
        ${vistas.map(v => `<tr><td>${escapar(v.name)}</td><td><code>${escapar(v.sql)}</code></td><td class="acciones"><button class="editar" data-abrir="${escaparAtributo(v.name)}">Abrir en consola</button> <button class="eliminar" data-borrar="${escaparAtributo(v.name)}">Eliminar</button></td></tr>`).join("")}
      </tbody></table></div>` : '<p class="vacio">Todavía no hay vistas.</p>'}`;

    const avisar = (texto, error) => { this.zona.querySelector("#aviso").innerHTML = '<p class="' + (error ? "error" : "ok") + '">' + escapar(texto) + "</p>"; };
    const enviar = (id, ruta, armar, texto) => this.zona.querySelector(id).onsubmit = async e => {
      e.preventDefault();
      try {
        await this.llamar(ruta, armar(Object.fromEntries(new FormData(e.target).entries())));
        await this.render('<p class="ok">' + escapar(texto) + "</p>");
        recargarEntidades();
      } catch (err) { avisar(err.message, true); }
    };
    enviar("#f-campo", "agregar_campo", d => d, "Campo agregado.");
    enviar("#f-tabla", "crear_tabla", d => ({
      nombre: d.nombre,
      campos: d.campos.split("\n").map(l => l.trim()).filter(Boolean).map(l => { const [nombre, tipo] = l.split(/\s+/); return { nombre, tipo: tipo || "TEXT" }; })
    }), "Tabla creada.");
    enviar("#f-vista", "crear_vista", d => d, "Vista creada.");
    this.zona.querySelectorAll("[data-borrar]").forEach(b => b.onclick = async () => {
      if (!confirm("¿Eliminar la vista " + b.dataset.borrar + "?")) return;
      try { await this.llamar("eliminar_vista", { nombre: b.dataset.borrar }); this.render('<p class="ok">Vista eliminada.</p>'); } catch (err) { avisar(err.message, true); }
    });
    this.zona.querySelectorAll("[data-abrir]").forEach(b => b.onclick = () => {
      document.querySelector('#sistema [data-vista="consola"]').click();
      this.zona.querySelector("#sql").value = 'SELECT * FROM "' + b.dataset.abrir + '"';
      new RedkyberConsola().ejecutar();
    });
  }
}
