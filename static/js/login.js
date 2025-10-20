/**
 * Login Form Handler
 * Handles login form validation, submission, and user feedback
 */

// ============================================================================
// CONSTANTS
// ============================================================================

const CONFIG = {
  FLASH_DURATION: 5000,
  TOAST_DURATION: 3000,
  ANIMATION_DURATION: 500
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
  }
};

// ============================================================================
// LOGIN FORM CLASS
// ============================================================================

class LoginForm {
  constructor() {
    this.form = document.getElementById('loginForm');
    this.loginBtn = document.getElementById('loginBtn');
    this.usernameInput = document.getElementById('floatingUsername');
    this.passwordInput = document.getElementById('floatingPassword');
    this.originalBtnText = this.loginBtn.innerHTML;
    
    this.init();
  }

  // --------------------------------------------------------------------------
  // INITIALIZATION
  // --------------------------------------------------------------------------

  init() {
    if (!this.form) {
      console.error('Login form not found');
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

    // Input validation on blur
    [this.usernameInput, this.passwordInput].forEach(input => {
      if (input) {
        input.addEventListener('blur', () => this.validateInput(input));
        input.addEventListener('input', () => {
          if (input.classList.contains('is-invalid')) {
            this.validateInput(input);
          }
        });
      }
    });

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
    // Validate all inputs
    if (!this.validateForm()) {
      e.preventDefault();
      Utils.showToast('Bitte alle Felder ausfüllen', 'danger');
      return false;
    }

    // Show loading state AFTER a tiny delay to ensure form values are captured
    // This prevents the inputs from being disabled before form submission
    setTimeout(() => {
      this.setLoadingState(true);
    }, 10);
    
    return true;
  }

  validateForm() {
    let isValid = true;

    // Ensure inputs are available
    if (!this.usernameInput || !this.passwordInput) {
      console.error('Login inputs not found');
      return false;
    }

    // Validate username
    if (!this.validateInput(this.usernameInput)) {
      isValid = false;
    }

    // Validate password
    if (!this.validateInput(this.passwordInput)) {
      isValid = false;
    }

    return isValid;
  }

  // --------------------------------------------------------------------------
  // INPUT VALIDATION
  // --------------------------------------------------------------------------

  validateInput(input) {
    if (!input) return false;

    const value = input.value.trim();
    const isRequired = input.hasAttribute('required');

    if (isRequired && !value) {
      this.setInputInvalid(input);
      return false;
    }

    if (value) {
      this.setInputValid(input);
      return true;
    }

    this.clearInputValidation(input);
    return true;
  }

  setInputValid(input) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
  }

  setInputInvalid(input) {
    input.classList.remove('is-valid');
    input.classList.add('is-invalid');
  }

  clearInputValidation(input) {
    input.classList.remove('is-valid', 'is-invalid');
  }

  // --------------------------------------------------------------------------
  // UI STATE MANAGEMENT
  // --------------------------------------------------------------------------

  setLoadingState(isLoading) {
    if (isLoading) {
      this.loginBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Anmelden...';
      this.loginBtn.classList.add('btn-loading');
      this.loginBtn.disabled = true;
      
      // Use readOnly instead of disabled to ensure form values are submitted
      this.usernameInput.readOnly = true;
      this.passwordInput.readOnly = true;
    } else {
      this.loginBtn.innerHTML = this.originalBtnText;
      this.loginBtn.classList.remove('btn-loading');
      this.loginBtn.disabled = false;
      
      // Re-enable inputs
      this.usernameInput.readOnly = false;
      this.passwordInput.readOnly = false;
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
      // Small delay to ensure page is fully loaded
      setTimeout(() => this.usernameInput.focus(), 100);
    }
  }

  reset() {
    this.form.reset();
    this.clearAllValidation();
    this.setLoadingState(false);
  }

  clearAllValidation() {
    [this.usernameInput, this.passwordInput].forEach(input => {
      if (input) {
        this.clearInputValidation(input);
      }
    });
  }
}

// ============================================================================
// INITIALIZE APPLICATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  window.loginForm = new LoginForm();
});