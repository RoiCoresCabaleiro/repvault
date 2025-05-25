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
      const pesoInput = document.querySelector(`[name="peso_${clave}_${idx}"]`);
      const repsInput = document.querySelector(`[name="reps_${clave}_${idx}"]`);

      pesoInput.style.border = '';
      repsInput.style.border = '';

      const p = parseFloat(pesoInput.value);
      const r = parseInt(repsInput.value, 10);
      const validPeso = !isNaN(p) && 0 <= p && p <= 1000;
      const validReps = Number.isInteger(r) && 1 <= r && r <= 100;

      if (!validPeso || !validReps) {
        // 1) revertir check + shake
        cb.checked = false;
        cb.classList.add("checkbox-shake");

        // 2) borde rojo donde corresponda
        if (!validPeso) {
          pesoInput.style.border = '1px solid #f56565';
          pesoInput.focus();
        }
        if (!validReps) {
          repsInput.style.border = '1px solid #f56565';
          if (pesoInput.value.trim()) repsInput.focus();
        }

        // 3) calcular flags de rango y no vacío
        const pesoVal = pesoInput.value.trim();
        const repsVal = repsInput.value.trim();
        const anyOutOfRange = (!validPeso && pesoVal !== "") || (!validReps && repsVal !== "");
        const anyNonEmpty   = pesoVal !== "" || repsVal !== "";

        // 4) mostrar mensaje si hay fuera de rango Y al menos un campo no vacío
        if (anyOutOfRange && anyNonEmpty) {
          const row = cb.closest("tr");
          const errorRow = row.nextElementSibling;
          const errorDiv = errorRow.querySelector(".serie-error");
          errorDiv.textContent = "Rangos: PESO [0, 1000]kg | REPS [1, 100]";
          errorRow.style.display = "table-row";

          // limpiar mensaje tras 2s
          setTimeout(() => {
            errorRow.style.display = "none";
            errorDiv.textContent = "";
          }, 3000);
        }

        // 5) limpiar shake y bordes tras 2s
        setTimeout(() => {
          cb.classList.remove("checkbox-shake");
          pesoInput.style.border = '';
          repsInput.style.border = '';
        }, 5000);
      }
    });
  });

  // — 3. DESMARCAR SERIES INVALIDAS: caso vacío y caso fuera de rango —
  document.querySelectorAll('input[name^="peso_"], input[name^="reps_"]').forEach(input => {
    input.addEventListener("input", () => {
      const [, clave, idx] = input.name.split("_");
      const pesoInput = document.querySelector(`[name="peso_${clave}_${idx}"]`);
      const repsInput = document.querySelector(`[name="reps_${clave}_${idx}"]`);
      const checkbox = document.getElementById(`hecha_${clave}_${idx}`);

      const pesoVal = pesoInput.value.trim();
      const repsVal = repsInput.value.trim();
      const p = parseFloat(pesoVal);
      const r = parseInt(repsVal, 10);
      const validPeso = !isNaN(p) && 0 <= p && p <= 1000;
      const validReps = Number.isInteger(r) && 1 <= r && r <= 100;

      // Si la casilla estaba marcada
      if (checkbox.checked) {
        // CASO 3a: campo vacío
        if (pesoVal === "" || repsVal === "") {
          checkbox.checked = false;
          if (pesoVal === "") {
            pesoInput.style.border = '1px solid #f56565';
          }
          if (repsVal === "") {
            repsInput.style.border = '1px solid #f56565';
          }

          setTimeout(() => {
            pesoInput.style.border = '';
            repsInput.style.border = '';
          }, 5000);
          return;
        }

        // CASO 3b: fuera de rango (no vacío)
        if ((!validPeso && pesoVal !== "") || (!validReps && repsVal !== "")) {
          checkbox.checked = false;
          if (!validPeso) {
            pesoInput.style.border = '1px solid #f56565';
          }
          if (!validReps) {
            repsInput.style.border = '1px solid #f56565';
          }

          const row = input.closest("tr");
          const errorRow = row.nextElementSibling;
          const errorDiv = errorRow.querySelector(".serie-error");
          errorDiv.textContent = "Rangos:   PESO [0,1000kg]   |   REPS [1,100]";
          errorRow.style.display = "table-row";

          setTimeout(() => {
            pesoInput.style.border = '';
            repsInput.style.border = '';
            errorRow.style.display = "none";
            errorDiv.textContent = "";
          }, 3000);
        }
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
