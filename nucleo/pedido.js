// RedKyber · Proceso guiado "Nuevo pedido" en 3 pasos (cliente, aeronaves, confirmación)
// El navegador valida cada paso, pero la validación definitiva la hace el procedimiento
// nuevo_pedido de la API, que guarda el pedido y sus líneas en una sola transacción.
class RedkyberPedido {
  constructor(contenedor = "section") {
    this.zona = document.querySelector(contenedor);
    this.paso = 1;
    this.pedido = { cliente_id: "", fecha: new Date().toISOString().slice(0, 10), lineas: [] };
  }

  euros(v) { return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v || 0); }

  async render() {
    if (!this.clientes) {
      const [c, p] = await Promise.all(["clientes", "productos"].map(t => fetch("api/superapi.php?ruta=tabla&tabla=" + t).then(r => r.json())));
      this.clientes = c.registros.sort((a, b) => a.nombre.localeCompare(b.nombre)); this.productos = p.registros.sort((a, b) => a.precio - b.precio);
    }
    const nombres = ["Cliente", "Aeronaves", "Confirmación"];
    this.zona.innerHTML = `
      <div class="barra"><div><small>PROCESO GUIADO</small><h2>Nuevo pedido</h2></div></div>
      <ol class="pasos">${nombres.map((n, i) => `<li class="${i + 1 === this.paso ? "activo" : i + 1 < this.paso ? "hecho" : ""}">${n}</li>`).join("")}</ol>
      <div id="aviso"></div><div id="paso"></div>`;
    [null, this.pasoCliente, this.pasoLineas, this.pasoConfirmar][this.paso].call(this);
  }

  error(texto) { this.zona.querySelector("#aviso").innerHTML = '<p class="error"></p>'; this.zona.querySelector("#aviso .error").textContent = texto; }

  pasoCliente() {
    this.zona.querySelector("#paso").innerHTML = `<form id="f">
      <label>Cliente<select name="cliente" required><option value="">— Selecciona —</option>${this.clientes.map(c => `<option value="${c.identificador}"${String(c.identificador) === String(this.pedido.cliente_id) ? " selected" : ""}>${escapar(c.nombre)} (${escapar(c.pais)})</option>`).join("")}</select></label>
      <label>Fecha del pedido<input type="date" name="fecha" required value="${this.pedido.fecha}"></label>
      <button type="submit">Siguiente →</button></form>`;
    this.zona.querySelector("#f").onsubmit = e => {
      e.preventDefault(); const d = Object.fromEntries(new FormData(e.target).entries());
      if (!d.cliente) return this.error("Elige un cliente.");
      this.pedido.cliente_id = d.cliente; this.pedido.fecha = d.fecha; this.paso = 2; this.render();
    };
  }

  pasoLineas() {
    this.zona.querySelector("#paso").innerHTML = `<form id="f" class="en-linea">
      <label>Aeronave<select name="producto" required><option value="">— Selecciona —</option>${this.productos.map(p => `<option value="${p.identificador}">${escapar(p.nombre)} · ${this.euros(p.precio)}</option>`).join("")}</select></label>
      <label>Cantidad<input type="number" name="cantidad" min="1" max="500" step="1" value="1" required></label>
      <button type="submit">+ Agregar línea</button></form>
      <div class="tabla-contenedor"><table><thead><tr><th>Aeronave</th><th>Cantidad</th><th>Precio</th><th>Importe</th><th></th></tr></thead><tbody>
      ${this.pedido.lineas.map((l, i) => `<tr><td>${escapar(this.nombreProducto(l.producto_id))}</td><td>${l.cantidad}</td><td>${this.euros(this.precio(l.producto_id))}</td><td>${this.euros(l.cantidad * this.precio(l.producto_id))}</td><td class="acciones"><button class="eliminar" data-quitar="${i}">Quitar</button></td></tr>`).join("") || '<tr><td colspan="5" class="vacio">Todavía no hay líneas.</td></tr>'}
      </tbody></table></div>
      <p class="acciones-barra"><button class="secundario" id="atras">← Atrás</button><button id="siguiente">Siguiente →</button></p>`;
    this.zona.querySelector("#f").onsubmit = e => {
      e.preventDefault(); const d = Object.fromEntries(new FormData(e.target).entries());
      const existente = this.pedido.lineas.find(l => l.producto_id === d.producto);
      if (existente) existente.cantidad += Number(d.cantidad); else this.pedido.lineas.push({ producto_id: d.producto, cantidad: Number(d.cantidad) });
      this.render();
    };
    this.zona.querySelectorAll("[data-quitar]").forEach(b => b.onclick = () => { this.pedido.lineas.splice(b.dataset.quitar, 1); this.render(); });
    this.zona.querySelector("#atras").onclick = () => { this.paso = 1; this.render(); };
    this.zona.querySelector("#siguiente").onclick = () => this.pedido.lineas.length ? (this.paso = 3, this.render()) : this.error("Agrega al menos una línea.");
  }

  pasoConfirmar() {
    const cliente = this.clientes.find(c => String(c.identificador) === String(this.pedido.cliente_id));
    const total = this.pedido.lineas.reduce((a, l) => a + l.cantidad * this.precio(l.producto_id), 0);
    this.zona.querySelector("#paso").innerHTML = `
      <div class="kpis"><div><small>Cliente</small><strong class="pequeno">${escapar(cliente.nombre)}</strong></div><div><small>Fecha</small><strong class="pequeno">${this.pedido.fecha}</strong></div><div><small>Líneas</small><strong>${this.pedido.lineas.length}</strong></div><div><small>Total</small><strong>${this.euros(total)}</strong></div></div>
      <p class="acciones-barra"><button class="secundario" id="atras">← Atrás</button><button id="confirmar">Confirmar pedido</button></p>`;
    this.zona.querySelector("#atras").onclick = () => { this.paso = 2; this.render(); };
    this.zona.querySelector("#confirmar").onclick = async () => {
      const r = await fetch("api/superapi.php?ruta=procedimiento&nombre=nuevo_pedido", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(this.pedido)
      }).then(r => r.json());
      if (r.ok === false) return this.error(r.error);
      this.zona.innerHTML = `<div class="barra"><div><small>PROCESO GUIADO</small><h2>Pedido registrado</h2></div></div><p class="ok">Pedido n.º ${r.pedido} guardado por ${this.euros(r.total)}, en estado Pendiente.</p><button id="otro">Crear otro pedido</button>`;
      this.zona.querySelector("#otro").onclick = () => new RedkyberPedido().render();
    };
  }

  precio(id) { return Number(this.productos.find(p => String(p.identificador) === String(id)).precio); }
  nombreProducto(id) { return this.productos.find(p => String(p.identificador) === String(id)).nombre; }
}
