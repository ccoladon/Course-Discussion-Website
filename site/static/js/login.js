(() => {
  const TOKEN_KEY = "coursechat_token";
  if (localStorage.getItem(TOKEN_KEY)) {
    location.replace("/app/");
    return;
  }

  const emailForm = document.getElementById("email-form");
  const codeForm = document.getElementById("code-form");
  const emailInput = document.getElementById("email");
  const codeInput = document.getElementById("code");
  const alertBox = document.getElementById("alert");
  const sentTo = document.getElementById("sent-to");
  const backBtn = document.getElementById("back-btn");

  let email = "";

  function showAlert(message, tone = "error") {
    alertBox.textContent = message;
    alertBox.className =
      "mt-4 rounded-lg px-3 py-2 text-sm " +
      (tone === "warn"
        ? "bg-amber-50 text-amber-800 border border-amber-200"
        : tone === "ok"
        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
        : "bg-rose-50 text-rose-700 border border-rose-200");
  }

  function clearAlert() {
    alertBox.className = "mt-4 hidden rounded-lg px-3 py-2 text-sm";
    alertBox.textContent = "";
  }

  function formatError(data, fallback) {
    if (!data) return fallback;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    const first = Object.entries(data)[0];
    if (first) return `${first[0]}: ${[].concat(first[1]).join(" ")}`;
    return fallback;
  }

  async function post(path, body) {
    const response = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(formatError(data, `Request failed (${response.status})`));
    }
    return data;
  }

  function setBusy(form, busy) {
    form.querySelectorAll("button, input").forEach((el) => (el.disabled = busy));
  }

  emailForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert();
    setBusy(emailForm, true);
    try {
      email = emailInput.value.trim().toLowerCase();
      const data = await post("/auth/request-code/", { email });
      sentTo.textContent = email;
      emailForm.classList.add("hidden");
      codeForm.classList.remove("hidden");
      if (data.dev_code) {
        codeInput.value = data.dev_code;
        codeInput.select();
      } else {
        codeInput.focus();
      }
      if (!data.verified_domain) {
        showAlert(
          data.message || "This email domain isn't linked to a school yet.",
          "warn"
        );
      } else if (data.dev_code) {
        showAlert("Dev mode: the code was filled in automatically. Click Sign in.", "ok");
      }
    } catch (error) {
      showAlert(error.message);
    } finally {
      setBusy(emailForm, false);
    }
  });

  codeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert();
    setBusy(codeForm, true);
    try {
      const data = await post("/auth/confirm-code/", {
        email,
        code: codeInput.value.trim(),
      });
      localStorage.setItem(TOKEN_KEY, data.token);
      location.replace("/app/");
    } catch (error) {
      showAlert(error.message);
      codeInput.select();
      setBusy(codeForm, false);
    }
  });

  backBtn.addEventListener("click", () => {
    clearAlert();
    codeForm.classList.add("hidden");
    emailForm.classList.remove("hidden");
    codeInput.value = "";
    emailInput.focus();
  });
})();
