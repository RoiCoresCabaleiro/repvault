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
        // revertir check + shake
        cb.checked = false;
        cb.classList.add("checkbox-shake");

        // → aquí: borde rojo inline (funciona en claro y oscuro)
        if (!peso.value.trim()) {
          peso.style.border = '1px solid #f56565';
          peso.focus();
        }
        if (!reps.value.trim()) {
          reps.style.border = '1px solid #f56565';
          if (peso.value.trim()) reps.focus();
        }

        // limpiar después
        setTimeout(() => {
          cb.classList.remove("checkbox-shake");
          peso.style.border = '';
          reps.style.border = '';
        }, 1500);
      }
    });
  });

  // — 3. DESMARCAR SERIES INVALIDAS —
  document.querySelectorAll('input[name^="peso_"], input[name^="reps_"]').forEach(input => {
    input.addEventListener("input", () => {
      const [tipo, soid, idx] = input.name.split("_");
      const pesoVal = document.querySelector(`[name="peso_${soid}_${idx}"]`).value.trim();
      const repsVal = document.querySelector(`[name="reps_${soid}_${idx}"]`).value.trim();
      const checkbox = document.getElementById(`hecha_${soid}_${idx}`);
      if (checkbox && (!pesoVal || !repsVal)) {
        checkbox.checked = false;
      }
    });
  });

  // — 4. CONFIRMAR FINALIZACIÓN —
  const form = document.getElementById("form-actual");
  if (form && form.dataset.showConfirm === "true") {
    const finalizeUrl = form.dataset.finalizeUrl;
    if (confirm("¿Has acabado?\nSe eliminarán todas las series inválidas o sin marcar como completadas.")) {
      form.action = finalizeUrl;
      form.submit();
    }
  }
});
