// Global variables
let currentUser = null;
let loginModal = null;
let registerModal = null;

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
    registerModal = new bootstrap.Modal(document.getElementById('registerModal'));
    
    // Add form submit event listeners
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
    
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    if (token) {
        currentUser = JSON.parse(localStorage.getItem('user'));
        updateUIForLoggedInUser();
    }
});

// Show/Hide modal functions
function showLoginModal() {
    document.getElementById('loginForm').reset();
    loginModal.show();
}

function showRegisterModal() {
    document.getElementById('registerForm').reset();
    registerModal.show();
}

// Authentication functions
async function handleRegister(event) {
    event.preventDefault();
    
    try {
        const formData = new FormData(event.target);
        const data = {
            email: formData.get('email'),
            mobile: formData.get('mobile'),
            password: formData.get('password')
        };
        
        console.log('Sending registration data:', data);
        
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        console.log('Registration response:', result);
        
        if (response.ok) {
            localStorage.setItem('token', result.token);
            localStorage.setItem('user', JSON.stringify(result.user));
            alert('Registration successful!');
            registerModal.hide();
            updateUIForLoggedInUser();
        } else {
            throw new Error(result.error || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert(error.message || 'An error occurred during registration');
    }
}

async function handleLogin(event) {
    event.preventDefault();
    
    try {
        const formData = new FormData(event.target);
        const username = formData.get('username');
        const password = formData.get('password');

        if (!username || !password) {
            throw new Error('Please fill in all fields');
        }

        // Determine if username is email or mobile
        const isEmail = username.includes('@');
        
        const data = {
            password: password
        };

        // Add either email or mobile to the request data
        if (isEmail) {
            data.email = username;
        } else {
            data.mobile = username;
        }
        
        console.log('Sending login data:', data);
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        console.log('Login response:', result);
        
        if (response.ok) {
            localStorage.setItem('token', result.token);
            localStorage.setItem('user', JSON.stringify(result.user));
            alert('Login successful!');
            loginModal.hide();
            updateUIForLoggedInUser();
        } else {
            throw new Error(result.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert(error.message || 'An error occurred during login');
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    currentUser = null;
    updateUIForLoggedOutUser();
}

// UI update functions
function updateUIForLoggedInUser() {
    document.getElementById('authButtons').classList.add('d-none');
    document.getElementById('userMenu').classList.remove('d-none');
}

function updateUIForLoggedOutUser() {
    document.getElementById('authButtons').classList.remove('d-none');
    document.getElementById('userMenu').classList.add('d-none');
}

// Prediction functions
async function handlePrediction(event) {
    event.preventDefault();
    
    try {
        // Get form data
        const form = document.getElementById('predictionForm');
        const formData = new FormData(form);
        
        // Validate form data
        const eventType = formData.get('event_type');
        const expectedAttendees = formData.get('expected_attendees');
        const actualAttendees = formData.get('actual_attendees');

        if (!eventType || !expectedAttendees || !actualAttendees) {
            throw new Error('Please fill in all fields');
        }

        // Validate that expected attendees is not less than actual
        if (parseInt(expectedAttendees) < parseInt(actualAttendees)) {
            throw new Error('Expected attendees cannot be less than actual attendees');
        }

        const data = {
            event_type: eventType,
            expected_attendees: parseInt(expectedAttendees),
            actual_attendees: parseInt(actualAttendees)
        };

        console.log('Sending prediction data:', data);
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculating...';
        submitButton.disabled = true;
        
        // Make prediction request
        const response = await fetch('/api/predict/predict-wastage', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Prediction failed');
        }

        const result = await response.json();
        console.log('Prediction response:', result);
        
        // Update prediction results
        document.getElementById('wastageAmount').textContent = `${result.predicted_wastage} kg`;
        document.getElementById('attendanceDiff').textContent = 
            `Difference: ${Math.abs(result.attendance_difference)} ${result.attendance_difference > 0 ? 'fewer' : 'more'} people than expected`;
        document.getElementById('attendancePercent').textContent = 
            `${Math.abs(result.percentage_difference)}% ${result.percentage_difference > 0 ? 'lower' : 'higher'} attendance than expected`;
        
        // Show results section
        document.getElementById('predictionResults').classList.remove('d-none');
        
        // Smooth scroll to results
        document.getElementById('predictionResults').scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('Prediction error:', error);
        alert(error.message || 'An error occurred during prediction');
    } finally {
        // Reset button state
        const submitButton = document.getElementById('predictionForm').querySelector('button[type="submit"]');
        submitButton.innerHTML = '<i class="fas fa-calculator me-2"></i>Calculate Prediction';
        submitButton.disabled = false;
    }
}

// Location and charity search functions
async function searchCharities() {
    const locationInput = document.getElementById('locationInput').value.trim();
    if (!locationInput) {
        alert('Please enter a location');
        return;
    }

    showLoadingCharities(true);
    try {
        const response = await fetch(`/api/predict/find-charities?location=${encodeURIComponent(locationInput)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch charities');
        }

        const result = await response.json();
        displayCharities(result.charities);
    } catch (error) {
        console.error('Error fetching charities:', error);
        alert('Failed to fetch charities. Please try again.');
    } finally {
        showLoadingCharities(false);
    }
}

async function useCurrentLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        return;
    }

    showLoadingCharities(true);
    try {
        const position = await getCurrentPosition();
        const response = await fetch('/api/predict/find-charities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch charities');
        }

        const result = await response.json();
        displayCharities(result.charities);
    } catch (error) {
        console.error('Error getting location or fetching charities:', error);
        alert(error.message || 'Failed to get nearby charities. Please try entering your location manually.');
    } finally {
        showLoadingCharities(false);
    }
}

function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        });
    });
}

function showLoadingCharities(show) {
    const loadingElement = document.getElementById('loadingCharities');
    const charitiesSection = document.getElementById('charitiesSection');
    
    if (show) {
        loadingElement.classList.remove('d-none');
        charitiesSection.classList.add('d-none');
    } else {
        loadingElement.classList.add('d-none');
        charitiesSection.classList.remove('d-none');
    }
}

function displayCharities(charities) {
    const charitiesList = document.getElementById('charitiesList');
    charitiesList.innerHTML = '';
    
    if (!charities || charities.length === 0) {
        charitiesList.innerHTML = `
            <div class="col-12 text-center">
                <p class="text-muted">No charities or old age homes found in this area. Please try a different location.</p>
            </div>
        `;
        return;
    }
    
    charities.forEach(charity => {
        const charityCard = document.createElement('div');
        charityCard.className = 'col-md-6 mb-4';
        charityCard.innerHTML = `
            <div class="charity-card">
                <h5 class="charity-name">${charity.name}</h5>
                <div class="charity-details">
                    <p><i class="fas fa-map-marker-alt me-2"></i>${charity.address}</p>
                    <p><i class="fas fa-phone me-2"></i>${charity.phone}</p>
                    ${charity.website ? `
                        <p><i class="fas fa-globe me-2"></i>
                            <a href="${charity.website}" target="_blank" rel="noopener noreferrer">Visit Website</a>
                        </p>
                    ` : ''}
                    <p><i class="fas fa-route me-2"></i>${charity.distance.toFixed(1)} km away</p>
                    <p><i class="fas fa-tag me-2"></i>${charity.type}</p>
                </div>
                <div class="charity-footer">
                    <div class="charity-actions">
                        ${charity.website ? `
                            <a href="${charity.website}" target="_blank" rel="noopener noreferrer" 
                               class="btn btn-outline-primary btn-sm me-2">
                                <i class="fas fa-globe me-1"></i>Website
                            </a>
                        ` : ''}
                        <button class="btn btn-primary btn-sm" onclick="contactCharity('${charity.phone}', '${charity.website || ''}')">
                            <i class="fas fa-phone me-1"></i>Contact
                        </button>
                    </div>
                </div>
            </div>
        `;
        charitiesList.appendChild(charityCard);
    });
}

function contactCharity(phone, website) {
    let message = 'Contact Information:\n';
    message += `Phone: ${phone}\n`;
    if (website) {
        message += `Website: ${website}\n`;
    }
    message += '\nYou can contact this organization directly through their phone number or visit their website for more information.';
    alert(message);
}

// Smooth scroll to prediction section
function scrollToPrediction() {
    const predictionSection = document.getElementById('prediction');
    if (predictionSection) {
        predictionSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
} 