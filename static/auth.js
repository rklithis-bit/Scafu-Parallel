(() => {
  const form = document.querySelector("#auth-form");
  const signinTab = document.querySelector("#signin-tab");
  const signupTab = document.querySelector("#signup-tab");
  const usernameWrap = document.querySelector("#username-wrap");
  const username = document.querySelector("#username");
  const email = document.querySelector("#email");
  const password = document.querySelector("#password");
  const error = document.querySelector("#error");
  const submit = document.querySelector("#submit");
  if (!form || !submit || !error) return;
  let mode = "signin";
  let busy = false;

  function setMode(next) {
    if (busy) return;
    mode = next;
    signinTab.classList.toggle("active", mode === "signin");
    signupTab.classList.toggle("active", mode === "signup");
    usernameWrap.classList.toggle("hidden", mode !== "signup");
    username.required = mode === "signup";
    document.querySelector("#heading").textContent = mode === "signin" ? "Good to see you." : "Make it yours.";
    document.querySelector("#subheading").textContent = mode === "signin" ? "Your private corner of the internet." : "Create your account for your private space.";
    submit.innerHTML = (mode === "signin" ? "Sign in" : "Create account") + " <span>↗</span>";
    password.autocomplete = mode === "signin" ? "current-password" : "new-password";
    error.classList.add("hidden");
    error.textContent = "";
  }
  signinTab.addEventListener("click", () => setMode("signin"));
  signupTab.addEventListener("click", () => setMode("signup"));

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    error.classList.add("hidden");
    error.textContent = "";
    busy = true;
    submit.disabled = true;
    submit.textContent = mode === "signin" ? "Signing in…" : "Creating account…";
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        credentials: "same-origin",
        cache: "no-store",
        body: JSON.stringify({email: email.value.trim(), password: password.value, username: username.value.trim()})
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `Sign-in request failed (HTTP ${response.status}).`);
      if (!result.redirect) throw new Error("Login succeeded but the server did not return a destination. Please try again.");
      window.location.assign(result.redirect);
    } catch (e) {
      error.textContent = e instanceof TypeError
        ? "Could not reach SCAFU. Check your connection and refresh the page."
        : (e.message || "Something went wrong. Please try again.");
      error.classList.remove("hidden");
    } finally {
      busy = false;
      submit.disabled = false;
      submit.innerHTML = (mode === "signin" ? "Sign in" : "Create account") + " <span>↗</span>";
    }
  });
})();
