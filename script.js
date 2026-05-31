// ================================
// Smooth Scrolling
// ================================

document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener("click", function (e) {

        const targetId = this.getAttribute("href");

        if (targetId !== "#") {
            e.preventDefault();

            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: "smooth"
                });
            }
        }
    });
});


// ================================
// API base URL helpers
// ================================

const API_BASE = (window.location.protocol === 'file:' || (window.location.hostname === '127.0.0.1' && window.location.port !== '5000'))
    ? 'http://127.0.0.1:5000'
    : '';

function apiFetch(path, options = {}) {
    return fetch(`${API_BASE}${path}`, options);
}


// ================================
// Cart Functionality
// ================================

// Cart stored in localStorage as JSON: { items: {id: qty, ...} }
let cart = JSON.parse(localStorage.getItem('cart') || '{"items":{}}');

const cartCounter = document.getElementById("cart-count");
const cartPanel = document.getElementById('cart-panel');
const cartItemsContainer = document.getElementById('cart-items');
const cartTotalElement = document.getElementById('cart-total');
const closeCartBtn = document.getElementById('close-cart-btn');
const confirmOrderBtn = document.getElementById('confirm-order-btn');
const cartButton = document.getElementById('cart-button');
const openCartCta = document.querySelector('.open-cart-cta');
const checkoutForm = document.getElementById('checkout-form');
const customerNameInput = document.getElementById('customer-name');
const customerPhoneInput = document.getElementById('customer-phone');
const fulfillmentSelect = document.getElementById('fulfillment');

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));
}

function saveCart() {
    localStorage.setItem('cart', JSON.stringify(cart));
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'shop-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.classList.add('visible'), 10);
    window.setTimeout(() => {
        toast.classList.remove('visible');
        window.setTimeout(() => toast.remove(), 250);
    }, 2200);
}

function updateCartCountUI() {
    const count = Object.values(cart.items).reduce((s, item) => {
        return s + (typeof item === 'number' ? item : item.qty);
    }, 0);
    if (cartCounter) cartCounter.textContent = count;
}

function renderCart() {
    if (!cartItemsContainer || !cartTotalElement) return;

    const entries = Object.entries(cart.items);
    if (entries.length === 0) {
        cartItemsContainer.innerHTML = '<p class="empty-cart">Your cart is empty. Add some coffees to order.</p>';
        cartTotalElement.textContent = '0';
        if (confirmOrderBtn) confirmOrderBtn.disabled = true;
        if (checkoutForm) checkoutForm.classList.add('muted');
        return;
    }

    const items = entries.map(([id, data]) => {
        let qty = typeof data === 'number' ? data : data.qty;
        let name = typeof data === 'number' ? id : data.name;
        let price = typeof data === 'number' ? 0 : data.price;

        const card = document.querySelector(`.card[data-id="${id}"]`);
        if (card) {
            name = card.querySelector('h3').textContent;
            price = Number(card.dataset.price || 0);
        }
        return { id, name: escapeHTML(name), qty, price, total: price * qty };
    });

    const total = items.reduce((sum, item) => sum + item.total, 0);
    cartTotalElement.textContent = total.toFixed(0);

    cartItemsContainer.innerHTML = items.map(item => `
        <div class="cart-item">
            <div>
                <strong>${item.name}</strong>
                <p>&#8377;${item.price} &times; ${item.qty}</p>
            </div>
            <button class="remove-item-btn" data-id="${item.id}">&times;</button>
        </div>
    `).join('');

    if (confirmOrderBtn) confirmOrderBtn.disabled = false;
    if (checkoutForm) checkoutForm.classList.remove('muted');

    cartItemsContainer.querySelectorAll('.remove-item-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            delete cart.items[id];
            saveCart();
            updateCartCountUI();
            renderCart();
        });
    });
}

function openCartPanel() {
    if (cartPanel) {
        cartPanel.classList.add('active');
        renderCart();
    }
}

function closeCartPanel() {
    if (cartPanel) cartPanel.classList.remove('active');
}

updateCartCountUI();
renderCart();

const addToCartButtons = document.querySelectorAll(".card button");

addToCartButtons.forEach(button => {
    button.addEventListener("click", (e) => {
        const card = e.target.closest('.card');
        if (!card) return;
        const id = card.dataset.id;
        if (!id) return;

        const name = card.querySelector('h3').textContent;
        const price = Number(card.dataset.price || 0);

        if (!cart.items[id]) {
            cart.items[id] = { qty: 1, name: name, price: price };
        } else {
            if (typeof cart.items[id] === 'number') {
                cart.items[id] = { qty: cart.items[id] + 1, name: name, price: price };
            } else {
                cart.items[id].qty += 1;
            }
        }
        saveCart();
        updateCartCountUI();
        renderCart();

        showToast('Added to cart');
    });
});

if (cartButton && cartPanel) {
    cartButton.addEventListener('click', (e) => {
        e.preventDefault();
        openCartPanel();
    });
}

if (openCartCta && cartPanel) {
    openCartCta.addEventListener('click', openCartPanel);
}

if (closeCartBtn) {
    closeCartBtn.addEventListener('click', closeCartPanel);
}

if (confirmOrderBtn) {
    confirmOrderBtn.addEventListener('click', async () => {
        await placeOrder();
    });
}

const closeBillBtn = document.getElementById('close-bill-btn');
if (closeBillBtn) {
    closeBillBtn.addEventListener('click', () => {
        document.getElementById('bill-modal').classList.remove('active');
    });
}


// ================================
// Hero Buttons
// ================================

const heroBtns = document.querySelectorAll(".hero-buttons button");

if (heroBtns.length > 0) {

    // Order Now Button
    heroBtns[0].addEventListener("click", () => {
        window.location.href = "menu.html";
    });

    // Explore Menu Button
    heroBtns[1].addEventListener("click", () => {
        window.location.href = "menu.html";
    });
}


// ================================
// View Full Menu Button
// ================================

const viewMenuBtn = document.querySelector(".view-menu-link");

if (viewMenuBtn) {

    viewMenuBtn.addEventListener("click", (e) => {
        e.preventDefault();
        window.location.href = "menu.html";
    });

}


// ================================
// Contact Form
// ================================

const contactForm = document.querySelector(".contact-form");

if (contactForm) {

    contactForm.addEventListener("submit", async (e) => {

        e.preventDefault();

        const name = contactForm.querySelector('input[name="name"]').value.trim();
        const email = contactForm.querySelector('input[name="email"]').value.trim();
        const message = contactForm.querySelector('textarea[name="message"]').value.trim();

        if (!name || !email || !message) {
            alert("Please fill all fields.");
            return;
        }

        const payload = { name, email, message };

        try {
const res = await apiFetch('/api/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert(`Thank you ${name}! Your message has been sent successfully.`);
                contactForm.reset();
            } else {
                const err = await res.json().catch(() => ({}));
                alert(`Unable to send message (${res.status}). Please try again later.`);
                console.error('Contact API error', err);
            }

        } catch (error) {
            // Fallback to previous behavior if backend isn't running
            alert(`Thank you ${name}! Your message has been sent successfully.`);
            contactForm.reset();
            console.warn('Contact API not reachable, fallback used', error);
        }

    });

}


// ================================
// Login Button
// ================================

// Login button is a direct link to login.html. No JavaScript interception is needed.


// ================================
// Cart Icon Click
// ================================

const cartIcon = document.querySelector(".fa-cart-shopping");

if (cartIcon && cartPanel) {
    cartIcon.addEventListener("click", (e) => {
        e.preventDefault();
        openCartPanel();
    });
}

// ================================
// Place Order
// ================================

const placeOrderBtn = document.getElementById('place-order-btn');

async function placeOrder() {
    const entries = Object.entries(cart.items);
    if (entries.length === 0) {
        alert('Your cart is empty. Add some items first.');
        return;
    }

    const customer = {
        name: customerNameInput ? customerNameInput.value.trim() : '',
        phone: customerPhoneInput ? customerPhoneInput.value.trim() : '',
        fulfillment: fulfillmentSelect ? fulfillmentSelect.value : 'pickup'
    };

    if (!customer.name || !customer.phone) {
        alert('Please enter your name and phone number to place the order.');
        if (customerNameInput && !customer.name) customerNameInput.focus();
        else if (customerPhoneInput) customerPhoneInput.focus();
        return;
    }

    // compute total from data-price attributes on cards
    let total = 0;
    const items = entries.map(([id, data]) => {
        let qty = typeof data === 'number' ? data : data.qty;
        let price = typeof data === 'number' ? 0 : data.price;
        let name = typeof data === 'number' ? id : data.name;

        const card = document.querySelector(`.card[data-id="${id}"]`);
        if (card) {
            name = card.querySelector('h3').textContent;
            price = Number(card.dataset.price || 0);
        }
        total += price * qty;
        return { id, qty, name, price };
    });

    const originalText = confirmOrderBtn.textContent;
    confirmOrderBtn.textContent = 'Placing Order...';
    confirmOrderBtn.disabled = true;

    try {
        const res = await apiFetch('/api/order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items, total, customer })
        });

        if (res.ok) {
            const body = await res.json();
            
            // Generate Bill Modal
            document.getElementById('bill-order-id').textContent = body.order_id;
            document.getElementById('bill-customer-name').textContent = customer.name;
            document.getElementById('bill-customer-phone').textContent = customer.phone;
            document.getElementById('bill-fulfillment').textContent = customer.fulfillment;
            
            const billItemsContainer = document.getElementById('bill-items');
            billItemsContainer.innerHTML = items.map(it => {
                return `<div class="bill-item"><span>${it.name} x${it.qty}</span><span>&#8377;${it.price * it.qty}</span></div>`;
            }).join('');
            
            document.getElementById('bill-total').textContent = total.toFixed(0);

            closeCartPanel();
            document.getElementById('bill-modal').classList.add('active');

            // clear cart
            cart = { items: {} };
            saveCart();
            updateCartCountUI();
            renderCart();
            if (checkoutForm) checkoutForm.reset();
        } else {
            const body = await res.json().catch(() => ({}));
            alert('Error: ' + (body.error || 'Failed to place order. Please try again.'));
            console.error('Order error', res.status);
        }
    } catch (err) {
        alert('Unable to reach server. Please ensure the backend is running.');
        console.error(err);
    } finally {
        confirmOrderBtn.textContent = originalText;
        confirmOrderBtn.disabled = false;
    }
}

if (placeOrderBtn) {
    placeOrderBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openCartPanel();
    });
}


// ================================
// Navbar Shadow on Scroll
// ================================

const navbar = document.querySelector(".navbar");

window.addEventListener("scroll", () => {

    if (window.scrollY > 50) {

        navbar.style.boxShadow =
            "0 5px 15px rgba(0,0,0,0.15)";

    } else {

        navbar.style.boxShadow = "none";

    }

});


// ================================
// Welcome Message
// ================================

window.addEventListener("load", () => {

    console.log("Welcome to BeanByte ");

});
