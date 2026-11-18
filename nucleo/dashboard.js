// RedKyber · Dashboard con indicadores reales calculados en la API (ruta=indicadores)
class RedkyberDashboard {
  constructor(contenedor = "section") {
    this.zona = document.querySelector(contenedor);
  }

  euros(v) {
    return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 }).format(v || 0);
  }

  leerAjustes(claves) {
    let guardado = {};
    try { guardado = JSON.parse(localStorage.getItem("redkyber_dashboard")) || {}; } catch (e) {}
    const orden = (guardado.orden || []).filter(c => claves.includes(c));
    return { orden: [...orden, ...claves.filter(c => !orden.includes(c))], ocultos: (guardado.ocultos || []).filter(c => claves.includes(c)) };
  }

  guardarAjustes(ajustes) {
    try { localStorage.setItem("redkyber_dashboard", JSON.stringify(ajustes)); } catch (e) {}
  }

  async render() {
    this.zona.innerHTML = '<div class="vacio">Cargando dashboard…</div>';
    try {
      const { kpi, series } = await fetch("api/superapi.php?ruta=indicadores").then(r => r.json());
      this.zona.innerHTML = `
        <div class="barra"><div><small>VISIÓN GENERAL</small><h2>Dashboard</h2></div><div class="acciones-barra"><button type="button" class="secundario" id="personalizar">Personalizar</button></div></div>
        <div id="ajustes" class="ajustes" hidden></div>
        <div class="kpis">
          <div><small>Facturación total</small><strong>${this.euros(kpi.facturacion)}</strong></div>
          <div><small>Pedidos</small><strong>${kpi.pedidos ?? "—"}</strong></div>
          <div><small>Ticket medio</small><strong>${this.euros(kpi.ticket_medio)}</strong></div>
          <div><small>Pedidos sin entregar</small><strong>${kpi.pendientes ?? "—"}</strong></div>
          <div><small>Plantilla</small><strong>${kpi.empleados ?? "—"}</strong></div>
        </div>
        <div class="rejilla-graficas" id="graficas-dashboard"></div>`;

      // [serie, tipo de gráfica, título]
      const paneles = [
        ["ventas_mes", "area", "Facturación por mes"],
        ["pedidos_estado", "anillo", "Pedidos por estado"],
        ["clientes_top", "horizontal", "Mejores clientes (€)"],
        ["ventas_pais", "tarta", "Ventas por país"],
        ["unidades_tipo", "barras", "Aviones vendidos por tipo"],
        ["salario_departamento", "radar", "Salario medio por departamento"],
        ["stock_tipo", "lineas", "Stock de componentes por tipo"]
      ];
      const rejilla = this.zona.querySelector("#graficas-dashboard");
      const disponibles = paneles.filter(([clave]) => series[clave]?.length);
      // Orden y paneles ocultos se guardan en el navegador de cada usuario
      let ajustes = this.leerAjustes(disponibles.map(p => p[0]));
      const pintar = () => {
        rejilla.innerHTML = "";
        ajustes.orden.filter(c => !ajustes.ocultos.includes(c)).forEach(clave => {
          const [, tipo, titulo] = disponibles.find(p => p[0] === clave);
          const tarjeta = document.createElement("div");
          tarjeta.className = "tarjeta-grafica"; tarjeta.draggable = true; tarjeta.dataset.clave = clave;
          rejilla.appendChild(tarjeta);
          RedkyberGraficas.crear(tarjeta, tipo, series[clave].map(s => s.etiqueta), series[clave].map(s => s.valor), titulo);
          tarjeta.ondragstart = e => { e.dataTransfer.setData("text/plain", clave); tarjeta.classList.add("arrastrando"); };
          tarjeta.ondragend = () => tarjeta.classList.remove("arrastrando");
          tarjeta.ondragover = e => e.preventDefault();
          tarjeta.ondrop = e => {
            e.preventDefault();
            const origen = e.dataTransfer.getData("text/plain");
            if (!origen || origen === clave) return;
            ajustes.orden.splice(ajustes.orden.indexOf(origen), 1);
            ajustes.orden.splice(ajustes.orden.indexOf(clave), 0, origen);
            this.guardarAjustes(ajustes); pintar();
          };
        });
      };
      const panelAjustes = this.zona.querySelector("#ajustes");
      this.zona.querySelector("#personalizar").onclick = () => {
        panelAjustes.hidden = !panelAjustes.hidden;
        panelAjustes.innerHTML = "<small>Arrastra las gráficas para cambiar el orden. Marca las que quieres ver:</small>" +
          disponibles.map(([c, , t]) => `<label><input type="checkbox" data-c="${c}"${ajustes.ocultos.includes(c) ? "" : " checked"}> ${escapar(t)}</label>`).join("") +
          '<button type="button" class="secundario" id="restablecer">Restablecer</button>';
        panelAjustes.querySelectorAll("[data-c]").forEach(i => i.onchange = () => {
          ajustes.ocultos = i.checked ? ajustes.ocultos.filter(c => c !== i.dataset.c) : [...ajustes.ocultos, i.dataset.c];
          this.guardarAjustes(ajustes); pintar();
        });
        panelAjustes.querySelector("#restablecer").onclick = () => { ajustes = { orden: disponibles.map(p => p[0]), ocultos: [] }; this.guardarAjustes(ajustes); pintar(); this.zona.querySelector("#personalizar").click(); this.zona.querySelector("#personalizar").click(); };
      };
      pintar();
    } catch (e) {
      this.zona.innerHTML = '<p class="vacio">No se pudo cargar el dashboard: ' + escapar(e.message) + "</p>";
    }
  }
}
