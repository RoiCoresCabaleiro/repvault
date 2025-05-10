document.addEventListener("DOMContentLoaded", () => {
  // — 1. CRONÓMETRO —
  const cron = document.getElementById("cronometro");
  if (cron) {
    const inicioTxt = cron.dataset.inicio;          // "DD/MM/YYYY HH:MM:SS"
    const [, time] = inicioTxt.split(" ");
    const [h, m, s] = time.split(":").map(Number);
    const inicio = new Date();
    inicio.setHours(h, m, s, 0);

    function tick() {
      const diff = Math.floor((Date.now() - inicio.getTime()) / 1000);
      const H = String(Math.floor(diff / 3600)).padStart(2, "0");
      const M = String(Math.floor((diff % 3600) / 60)).padStart(2, "0");
      const S = String(diff % 60).padStart(2, "0");
      cron.textContent = `${H}:${M}:${S}`;
    }
    tick();
    setInterval(tick, 1000);
  }

  // — 2. VALIDACIÓN & SHAKE DE CHECKBOXES —
  document.querySelectorAll(".custom-checkbox").forEach(cb => {
    cb.addEventListener("change", () => {
      const [, clave, idx] = cb.name.split("_");
      const peso = document.querySelector(`[name="peso_${clave}_${idx}"]`);
      const reps = document.querySelector(`[name="reps_${clave}_${idx}"]`);

      if (!peso.value.trim() || !reps.value.trim()) {
        // revertir check
        cb.checked = false;
        // shake
        cb.classList.add("checkbox-shake");
        // resaltar y foco
        if (!peso.value.trim()) peso.classList.add("border-red-500"), peso.focus();
        if (!reps.value.trim()) reps.classList.add("border-red-500"),
          peso.value.trim() && reps.focus();

        // limpiar después
        setTimeout(() => {
          cb.classList.remove("checkbox-shake");
          peso.classList.remove("border-red-500");
          reps.classList.remove("border-red-500");
        }, 1500);
      }
    });
  });

  // — 3. CONFIRMAR FINALIZACIÓN —
  const form = document.getElementById("form-actual");
  if (form && form.dataset.showConfirm === "true") {
    const finalizeUrl = form.dataset.finalizeUrl;
    if (confirm("¿Has acabado?\nSe eliminarán todas las series inválidas o sin marcar como completadas.")) {
      form.action = finalizeUrl;
      form.submit();
    }
  }
});
