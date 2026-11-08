/* Mapa de la red (Cytoscape.js, servido desde /static/vendor: la CSP solo permite scripts propios).
   Color = comunidad, tamano = PageRank. Un clic en un punto abre el perfil. Sin animaciones. */
(function () {
  "use strict";

  var PALETA = ["#4da3ff", "#7ee8ae", "#ffb454", "#ff8aa5", "#b794f6", "#5eead4", "#f6e05e", "#fca5a5"];
  var SIN_COMUNIDAD = "#8793a6";

  function colorDe(comunidad) {
    return comunidad ? PALETA[(comunidad - 1) % PALETA.length] : SIN_COMUNIDAD;
  }

  /* Tamano del punto segun su PageRank, entre 20 y 64 px. */
  function tamanoNodo(pagerank, minimo, maximo) {
    if (pagerank === null || pagerank === undefined) { return 20; }
    var rango = maximo - minimo;
    return Math.round(20 + 44 * (rango > 0 ? (pagerank - minimo) / rango : 0.5));
  }

  function armarElementos(datos) {
    var valores = datos.nodos.map(function (n) { return n.pagerank; }).filter(function (v) { return v !== null && v !== undefined; });
    var minimo = valores.length ? Math.min.apply(null, valores) : 0;
    var maximo = valores.length ? Math.max.apply(null, valores) : 0;
    var elementos = [];
    datos.nodos.forEach(function (n) {
      elementos.push({ data: {
        id: n.id, etiqueta: n.corto, nombre: n.nombre, titular: n.titular || "", comunidad: n.comunidad,
        color: colorDe(n.comunidad), tamano: tamanoNodo(n.pagerank, minimo, maximo), yo: n.yo ? 1 : 0
      } });
    });
    datos.aristas.forEach(function (a, i) {
      elementos.push({ data: { id: "e" + i, source: a.origen, target: a.destino } });
    });
    return elementos;
  }

  function estilos() {
    return [
      { selector: "node", style: {
        "background-color": "data(color)", "width": "data(tamano)", "height": "data(tamano)",
        "label": "data(etiqueta)", "color": "#f5f8ff", "font-size": 11, "text-valign": "bottom", "text-margin-y": 4,
        "text-outline-color": "#0a0c10", "text-outline-width": 2, "border-width": 1, "border-color": "#0a0c10"
      } },
      { selector: "node[yo = 1]", style: { "border-width": 3, "border-color": "#ffffff" } },
      { selector: "edge", style: { "width": 1, "line-color": "rgba(146, 176, 224, 0.35)", "curve-style": "haystack" } },
      { selector: ".atenuado", style: { "opacity": 0.18 } },
      { selector: "node:selected", style: { "border-width": 3, "border-color": "#ffffff" } }
    ];
  }

  function leyenda(contenedor, comunidades) {
    contenedor.innerHTML = "";
    comunidades.forEach(function (c) {
      var li = document.createElement("li");
      var punto = document.createElement("span");
      punto.className = "punto-color";
      punto.style.backgroundColor = colorDe(c.numero);
      punto.setAttribute("aria-hidden", "true");
      li.appendChild(punto);
      li.appendChild(document.createTextNode("Comunidad " + c.numero + ": " + c.etiqueta + " (" + c.miembros + ")"));
      contenedor.appendChild(li);
    });
  }

  function iniciar() {
    var contenedor = document.getElementById("mapa-red");
    var info = document.getElementById("info-mapa");
    if (!contenedor || typeof cytoscape === "undefined") { return; }
    fetch(contenedor.getAttribute("data-url"), { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) { throw new Error(String(r.status)); } return r.json(); })
      .then(function (datos) {
        if (!datos.nodos.length) { info.textContent = "Todavia no hay personas para mostrar en el mapa."; return; }
        var cy = cytoscape({
          container: contenedor, elements: armarElementos(datos), style: estilos(),
          layout: { name: "cose", animate: false, nodeRepulsion: 9000, idealEdgeLength: 70, padding: 24 },
          minZoom: 0.3, maxZoom: 3, wheelSensitivity: 0.25
        });
        leyenda(document.getElementById("leyenda-mapa"), datos.comunidades);
        info.textContent = datos.nodos.length + " personas y " + datos.aristas.length + " conexiones. Toca una persona para abrir su perfil.";
        cy.on("mouseover", "node", function (e) {
          var n = e.target;
          cy.elements().addClass("atenuado");
          n.closedNeighborhood().removeClass("atenuado");
          info.textContent = n.data("nombre") + (n.data("titular") ? " · " + n.data("titular") : "") +
            (n.data("comunidad") ? " · Comunidad " + n.data("comunidad") : "");
        });
        cy.on("mouseout", "node", function () {
          cy.elements().removeClass("atenuado");
          info.textContent = datos.nodos.length + " personas y " + datos.aristas.length + " conexiones. Toca una persona para abrir su perfil.";
        });
        cy.on("tap", "node", function (e) { window.location.href = "/perfil/" + encodeURIComponent(e.target.id()); });
      })
      .catch(function () { info.textContent = "No se pudo cargar el mapa. La misma informacion esta en texto en la pagina de analitica."; });
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", iniciar); } else { iniciar(); }
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { colorDe: colorDe, tamanoNodo: tamanoNodo, armarElementos: armarElementos, estilos: estilos, PALETA: PALETA };
  }
})();
