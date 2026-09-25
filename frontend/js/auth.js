// MedSecure Authentication Handler

const Auth = {
  currentDoctor: null,

  init() {
    this.bindEvents();
    this.checkSession();
  },

  bindEvents() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
      loginForm.addEventListener('submit', (e) => this.handleLogin(e));
    }

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
      registerForm.addEventListener('submit', (e) => this.handleRegister(e));
    }

    const toRegisterLink = document.getElementById('toRegisterLink');
    if (toRegisterLink) {
      toRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('loginCard').style.display = 'none';
        document.getElementById('registerCard').style.display = 'block';
      });
    }

    const toLoginLink = document.getElementById('toLoginLink');
    if (toLoginLink) {
      toLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('registerCard').style.display = 'none';
        document.getElementById('loginCard').style.display = 'block';
      });
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => this.logout());
    }

    window.addEventListener('auth:expired', () => {
      this.showAuthModal();
      window.showToast('Session expired. Please log in again.', 'warning');
    });
  },

  async checkSession() {
    const token = API.getToken();
    if (!token) {
      this.showAuthModal();
      return;
    }

    try {
      const doctor = await API.getProfile();
      this.currentDoctor = doctor;
      this.updateDoctorUI(doctor);
      this.hideAuthModal();
      window.dispatchEvent(new CustomEvent('auth:ready'));
    } catch (err) {
      API.removeToken();
      this.showAuthModal();
    }
  },

  async handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';

      const res = await API.login(email, password);
      API.setToken(res.access_token);
      this.currentDoctor = res.doctor;
      this.updateDoctorUI(res.doctor);
      this.hideAuthModal();

      window.showToast(`Welcome back, ${res.doctor.name}!`, 'success');
      window.dispatchEvent(new CustomEvent('auth:ready'));
    } catch (err) {
      window.showToast(err.message || 'Login failed. Please check credentials.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Secure Doctor Login';
    }
  },

  async handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    const specialty = document.getElementById('regSpecialty').value.trim();
    const phone = document.getElementById('regPhone').value.trim();
    const submitBtn = e.target.querySelector('button[type="submit"]');

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registering...';

      await API.register({ name, email, password, specialty, phone });
      window.showToast('Registration successful! Please log in now.', 'success');

      // Switch back to login form
      document.getElementById('registerCard').style.display = 'none';
      document.getElementById('loginCard').style.display = 'block';
      document.getElementById('loginEmail').value = email;
      document.getElementById('loginPassword').focus();
    } catch (err) {
      window.showToast(err.message || 'Registration failed.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Register Doctor Account';
    }
  },

  logout() {
    API.removeToken();
    API.removeUSBToken();
    this.currentDoctor = null;
    this.showAuthModal();
    window.showToast('Logged out securely.', 'info');
  },

  showAuthModal() {
    const modal = document.getElementById('authModalOverlay');
    if (modal) modal.style.display = 'flex';
  },

  hideAuthModal() {
    const modal = document.getElementById('authModalOverlay');
    if (modal) modal.style.display = 'none';
  },

  updateDoctorUI(doctor) {
    const nameEls = document.querySelectorAll('.doctor-name-display');
    nameEls.forEach((el) => (el.textContent = doctor.name));

    const specialtyEls = document.querySelectorAll('.doctor-specialty-display');
    specialtyEls.forEach((el) => (el.textContent = doctor.specialty || 'General Practitioner'));

    const emailEls = document.querySelectorAll('.doctor-email-display');
    emailEls.forEach((el) => (el.textContent = doctor.email));

    const hospitalEls = document.querySelectorAll('.doctor-hospital-display');
    hospitalEls.forEach((el) => (el.textContent = doctor.hospital_name || 'FedMedX Memorial'));

    const avatarEls = document.querySelectorAll('.doctor-avatar-initials');
    const initials = doctor.name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();
    avatarEls.forEach((el) => (el.textContent = initials || 'MD'));
  },
};

window.Auth = Auth;
