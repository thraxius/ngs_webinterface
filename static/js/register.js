/**
 * Registration Form Handler
 * Handles registration form validation, password strength checking, and submission
 */

// ============================================================================
// CONSTANTS
// ============================================================================

const CONFIG = {
  FLASH_DURATION: 5000,
  TOAST_DURATION: 3000,
  ANIMATION_DURATION: 500,
  MIN_USERNAME_LENGTH: 4,
  MIN_PASSWORD_LENGTH: 6,
  PASSWORD_CHECKS: {
    length: 6,
    uppercase: /[A-Z]/,
    lowercase: /[a-z]/,
    number: /[0-9]/
  }
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const Utils = {
  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  /**
   * Show toast notification
   */
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `flash ${type} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `<i class="fas fa-info-circle me-2"></i>${Utils.escapeHtml(message)}`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.transition = `opacity ${CONFIG.ANIMATION_DURATION}ms ease-out`;
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), CONFIG.ANIMATION_DURATION);
    }, CONFIG.TOAST_DURATION);
  },

  /**
   * Auto-hide flash messages
   */
  setupFlashMessages() {
    document.querySelectorAll('.flash').forEach(flash => {
      setTimeout(() => {
        flash.style.transition = `opacity ${CONFIG.ANIMATION_DURATION}ms ease-out`;
        flash.style.opacity = '0';
        setTimeout(() => flash.remove(), CONFIG.ANIMATION_DURATION);
      }, CONFIG.FLASH_DURATION);
    });
  },

  /**
   * Validate email format
   */
  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  /**
   * Validate username format
   */
  isValidUsername(username) {
    // Only letters, numbers, and underscores
    const usernameRegex = /^[a-zA-Z0-9_]+$/;
    return username.length >= CONFIG.MIN_USERNAME_LENGTH && usernameRegex.test(username);
  }
};

// ============================================================================
// PASSWORD STRENGTH CHECKER
// ============================================================================

class PasswordStrengthChecker {
  constructor() {
    this.strengthFill = document.getElementById('strengthFill');
    this.strengthText = document.getElementById('strengthText');
    this.strengthContainer = document.getElementById('passwordStrength');
    
    this.requirements = {
      length: document.getElementById('req-length'),
      uppercase: document.getElementById('req-uppercase'),
      lowercase: document.getElementById('req-lowercase'),
      number: document.getElementById('req-number')
    };
  }

  /**
   * Check password strength and update UI
   */
  check(password) {
    if (!password) {
      this.hide();
      return { score: 0, strength: 'none' };
    }

    this.show();

    const checks = {
      length: password.length >= CONFIG.PASSWORD_CHECKS.length,
      uppercase: CONFIG.PASSWORD_CHECKS.uppercase.test(password),
      lowercase: CONFIG.PASSWORD_CHECKS.lowercase.test(password),
      number: CONFIG.PASSWORD_CHECKS.number.test(password)
    };

    // Update requirement indicators
    Object.keys(checks).forEach(key => {
      const element = this.requirements[key];
      const icon = element.querySelector('i');
      
      if (checks[key]) {
        element.classList.remove('unmet');
        element.classList.add('met');
        icon.className = 'fas fa-check';
      } else {
        element.classList.remove('met');
        element.classList.add('unmet');
        icon.className = 'fas fa-times';
      }
    });

    // Calculate strength score
    const score = Object.values(checks).filter(Boolean).length;
    const result = this.getStrengthLevel(score);

    // Update visual indicator
    this.updateStrengthBar(result);

    return { score, strength: result.strength, allChecksMet: score === 4 };
  }

  /**
   * Get strength level based on score
   */
  getStrengthLevel(score) {
    const levels = {
      0: { strength: 'none', class: 'strength-none', label: 'Keine Eingabe' },
      1: { strength: 'weak', class: 'strength-weak', label: 'Schwach' },
      2: { strength: 'fair', class: 'strength-fair', label: 'Mäßig' },
      3: { strength: 'good', class: 'strength-good', label: 'Gut' },
      4: { strength: 'strong', class: 'strength-strong', label: 'Stark' }
    };

    return levels[score] || levels[0];
  }

  /**
   * Update strength bar visual
   */
  updateStrengthBar(result) {
    this.strengthFill.className = `strength-fill ${result.class}`;
    this.strengthText.textContent = `Passwort-Stärke: ${result.label}`;
  }

  /**
   * Show strength indicator
   */
  show() {
    if (this.strengthContainer) {
      this.strengthContainer.style.display = 'block';
    }
  }

  /**
   * Hide strength indicator
   */
  hide() {
    if (this.strengthContainer) {
      this.strengthContainer.style.display = 'none';
    }
  }
}

// ============================================================================
// REGISTRATION FORM CLASS
// ============================================================================

class RegistrationForm {
  constructor() {
    this.form = document.getElementById('registerForm');
    this.registerBtn = document.getElementById('registerBtn');
    this.usernameInput = document.getElementById('floatingUsername');
    this.emailInput = document.getElementById('floatingEmail');
    this.passwordInput = document.getElementById('floatingPassword');
    this.password2Input = document.getElementById('floatingPassword2');
    this.originalBtnText = this.registerBtn.innerHTML;
    
    // Validation message containers
    this.usernameValidation = document.getElementById('usernameValidation');
    this.emailValidation = document.getElementById('emailValidation');
    this.password2Validation = document.getElementById('password2Validation');
    
    // Password strength checker
    this.passwordChecker = new PasswordStrengthChecker();
    
    this.init();
  }

  // --------------------------------------------------------------------------
  // INITIALIZATION
  // --------------------------------------------------------------------------

  init() {
    if (!this.form) {
      console.error('Registration form not found');
      return;
    }

    this.setupEventListeners();
    this.setupValidation();
    Utils.setupFlashMessages();
    this.focusFirstInput();
  }

  setupEventListeners() {
    // Form submission
    this.form.addEventListener('submit', (e) => this.handleSubmit(e));

    // Username validation
    if (this.usernameInput) {
      this.usernameInput.addEventListener('input', () => this.validateUsername());
      this.usernameInput.addEventListener('blur', () => this.validateUsername());
    }

    // Email validation
    if (this.emailInput) {
      this.emailInput.addEventListener('input', () => this.validateEmail());
      this.emailInput.addEventListener('blur', () => this.validateEmail());
    }

    // Password validation and strength checking
    if (this.passwordInput) {
      this.passwordInput.addEventListener('input', () => {
        this.checkPasswordStrength();
        this.validatePassword();
        if (this.password2Input.value) {
          this.validatePasswordMatch();
        }
      });
      this.passwordInput.addEventListener('blur', () => this.validatePassword());
    }

    // Password confirmation validation
    if (this.password2Input) {
      this.password2Input.addEventListener('input', () => this.validatePasswordMatch());
      this.password2Input.addEventListener('blur', () => this.validatePasswordMatch());
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => this.handleKeyboardNavigation(e));
  }

  setupValidation() {
    // Add Bootstrap validation classes
    this.form.classList.add('needs-validation');
  }

  // --------------------------------------------------------------------------
  // FORM SUBMISSION
  // --------------------------------------------------------------------------

  handleSubmit(e) {
    // Validate all fields
    if (!this.validateForm()) {
      e.preventDefault();
      Utils.showToast('Bitte korrigieren Sie die Fehler im Formular', 'danger');
      return false;
    }

    // Show loading state AFTER a tiny delay to ensure form values are captured
    setTimeout(() => {
      this.setLoadingState(true);
    }, 10);
    
    return true;
  }

  validateForm() {
    let isValid = true;

    // Validate username
    if (!this.validateUsername()) {
      isValid = false;
    }

    // Validate email
    if (!this.validateEmail()) {
      isValid = false;
    }

    // Validate password
    if (!this.validatePassword()) {
      isValid = false;
    }

    // Validate password match
    if (!this.validatePasswordMatch()) {
      isValid = false;
    }

    return isValid;
  }

  // --------------------------------------------------------------------------
  // USERNAME VALIDATION
  // --------------------------------------------------------------------------

  validateUsername() {
    if (!this.usernameInput) return false;

    const username = this.usernameInput.value.trim();
    let message = '';
    let isValid = true;

    if (!username) {
      message = this.createValidationMessage('invalid', 'Benutzername ist erforderlich');
      isValid = false;
    } else if (username.length < CONFIG.MIN_USERNAME_LENGTH) {
      message = this.createValidationMessage('invalid', `Mindestens ${CONFIG.MIN_USERNAME_LENGTH} Zeichen`);
      isValid = false;
    } else if (!Utils.isValidUsername(username)) {
      message = this.createValidationMessage('invalid', 'Nur Buchstaben, Zahlen und Unterstriche erlaubt');
      isValid = false;
    } else {
      message = this.createValidationMessage('valid', 'Gültiger Benutzername');
    }

    this.usernameValidation.innerHTML = message;
    this.updateInputValidation(this.usernameInput, isValid);
    
    return isValid;
  }

  // --------------------------------------------------------------------------
  // EMAIL VALIDATION
  // --------------------------------------------------------------------------

  validateEmail() {
    if (!this.emailInput) return false;

    const email = this.emailInput.value.trim();
    let message = '';
    let isValid = true;

    if (!email) {
      message = this.createValidationMessage('invalid', 'E-Mail Adresse ist erforderlich');
      isValid = false;
    } else if (!Utils.isValidEmail(email)) {
      message = this.createValidationMessage('invalid', 'Ungültige E-Mail Adresse');
      isValid = false;
    } else {
      message = this.createValidationMessage('valid', 'Gültige E-Mail Adresse');
    }

    this.emailValidation.innerHTML = message;
    this.updateInputValidation(this.emailInput, isValid);
    
    return isValid;
  }

  // --------------------------------------------------------------------------
  // PASSWORD VALIDATION
  // --------------------------------------------------------------------------

  checkPasswordStrength() {
    if (!this.passwordInput) return;

    const password = this.passwordInput.value;
    return this.passwordChecker.check(password);
  }

  validatePassword() {
    if (!this.passwordInput) return false;

    const password = this.passwordInput.value;
    const strengthResult = this.checkPasswordStrength();

    if (!password) {
      this.updateInputValidation(this.passwordInput, false);
      return false;
    }

    const isValid = strengthResult.allChecksMet;
    this.updateInputValidation(this.passwordInput, isValid);
    
    return isValid;
  }

  // --------------------------------------------------------------------------
  // PASSWORD MATCH VALIDATION
  // --------------------------------------------------------------------------

  validatePasswordMatch() {
    if (!this.password2Input) return false;

    const password = this.passwordInput ? this.passwordInput.value : '';
    const password2 = this.password2Input.value;
    let message = '';
    let isValid = true;

    if (!password2) {
      message = this.createValidationMessage('invalid', 'Passwort-Wiederholung ist erforderlich');
      isValid = false;
    } else if (password !== password2) {
      message = this.createValidationMessage('invalid', 'Passwörter stimmen nicht überein');
      isValid = false;
    } else {
      message = this.createValidationMessage('valid', 'Passwörter stimmen überein');
    }

    this.password2Validation.innerHTML = message;
    this.updateInputValidation(this.password2Input, isValid);
    
    return isValid;
  }

  // --------------------------------------------------------------------------
  // VALIDATION HELPERS
  // --------------------------------------------------------------------------

  createValidationMessage(type, text) {
    const icon = type === 'valid' ? 'fas fa-check' : 'fas fa-times';
    const className = type === 'valid' ? 'validation-message valid' : 'validation-message invalid';
    
    return `
      <div class="${className}">
        <i class="${icon}"></i>
        <span>${Utils.escapeHtml(text)}</span>
      </div>
    `;
  }

  updateInputValidation(input, isValid) {
    if (!input) return;

    if (isValid) {
      input.classList.remove('is-invalid');
      input.classList.add('is-valid');
    } else {
      input.classList.remove('is-valid');
      input.classList.add('is-invalid');
    }
  }

  clearInputValidation(input) {
    if (!input) return;
    input.classList.remove('is-valid', 'is-invalid');
  }

  // --------------------------------------------------------------------------
  // UI STATE MANAGEMENT
  // --------------------------------------------------------------------------

  setLoadingState(isLoading) {
    if (isLoading) {
      this.registerBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Registrierung läuft...';
      this.registerBtn.classList.add('btn-loading');
      this.registerBtn.disabled = true;
      
      // Use readOnly instead of disabled to ensure form values are submitted
      [this.usernameInput, this.emailInput, this.passwordInput, this.password2Input].forEach(input => {
        if (input) input.readOnly = true;
      });
    } else {
      this.registerBtn.innerHTML = this.originalBtnText;
      this.registerBtn.classList.remove('btn-loading');
      this.registerBtn.disabled = false;
      
      // Re-enable inputs
      [this.usernameInput, this.emailInput, this.passwordInput, this.password2Input].forEach(input => {
        if (input) input.readOnly = false;
      });
    }
  }

  // --------------------------------------------------------------------------
  // KEYBOARD NAVIGATION
  // --------------------------------------------------------------------------

  handleKeyboardNavigation(e) {
    if (e.key === 'Enter' && e.target.matches('.form-control')) {
      e.preventDefault();
      
      const inputs = Array.from(this.form.querySelectorAll('.form-control'));
      const currentIndex = inputs.indexOf(e.target);
      const nextInput = inputs[currentIndex + 1];
      
      if (nextInput) {
        nextInput.focus();
      } else {
        this.form.requestSubmit();
      }
    }
  }

  // --------------------------------------------------------------------------
  // UTILITY METHODS
  // --------------------------------------------------------------------------

  focusFirstInput() {
    if (this.usernameInput) {
      setTimeout(() => this.usernameInput.focus(), 100);
    }
  }

  reset() {
    this.form.reset();
    this.clearAllValidation();
    this.setLoadingState(false);
    this.passwordChecker.hide();
  }

  clearAllValidation() {
    [this.usernameInput, this.emailInput, this.passwordInput, this.password2Input].forEach(input => {
      if (input) {
        this.clearInputValidation(input);
      }
    });
    
    // Clear validation messages
    if (this.usernameValidation) this.usernameValidation.innerHTML = '';
    if (this.emailValidation) this.emailValidation.innerHTML = '';
    if (this.password2Validation) this.password2Validation.innerHTML = '';
  }
}

// ============================================================================
// INITIALIZE APPLICATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  window.registerForm = new RegistrationForm();
});