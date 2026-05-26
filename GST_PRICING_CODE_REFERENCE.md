# GST Pricing Module - Code Reference Guide

## 1. Database Model (flask_app/models.py)

```python
class Product(db.Model):
    # ... existing fields ...
    gst_percentage = db.Column(db.Float, default=18.0, nullable=False)
    gst_type = db.Column(db.String(20), default='inclusive', nullable=False)
    # ... other fields ...

    def to_dict(self):
        # ... existing calculations ...
        gst_pct = float(self.gst_percentage or 0)
        gst_type = self.gst_type or 'inclusive'

        if gst_type == 'inclusive':
            base_price = selling / (1 + gst_pct / 100) if gst_pct > 0 else selling
            gst_amount = selling - base_price
            final_price = selling
        else:
            base_price = selling
            gst_amount = round((selling * (gst_pct / 100)), 2)
            final_price = selling + gst_amount

        gst_amount = round(gst_amount, 2)
        base_price = round(base_price, 2)
        final_price = round(final_price, 2)

        return {
            # ... existing fields ...
            'gstPercentage': float(self.gst_percentage or 0),
            'gstType': gst_type,
            'basePrice': base_price,
            'gstAmount': gst_amount,
            'finalPrice': final_price,
            # ... other fields ...
        }
```

## 2. Database Migration (flask_app/__init__.py)

```python
def _ensure_product_schema():
    inspector = db.inspect(db.engine)
    if 'product' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('product')}

    missing_columns = {
        # ... existing columns ...
        'gst_percentage': 'FLOAT DEFAULT 18.0',
        'gst_type': "VARCHAR(20) DEFAULT 'inclusive'",
        # ... other columns ...
    }

    for column, definition in missing_columns.items():
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE product ADD COLUMN {column} {definition}'))

    db.session.commit()
```

## 3. Backend API (flask_app/routes/admin.py)

```python
@admin_bp.route('/api/products/save-advanced', methods=['POST'])
@login_required
@admin_required
def api_save_product_advanced():
    try:
        data = request.form if request.form else (request.get_json() or {})
        
        # ... existing fields ...
        gst_percentage = float(data.get('gstPercentage', 18))
        gst_type = str(data.get('gstType', 'inclusive')).strip().lower()
        if gst_type not in ['inclusive', 'exclusive']:
            gst_type = 'inclusive'
        
        # ... validation ...

    product = Product.query.get(product_id) if product_id else Product()
    
    # ... other assignments ...
    product.gst_percentage = gst_percentage
    product.gst_type = gst_type
    
    # ... save to database ...
    db.session.commit()
    return jsonify(success=True, product=product.to_dict())
```

## 4. Frontend HTML (flask_app/templates/admin/product_edit.html)

### GST Type Toggle UI
```html
<div class="form-group grid">
  <div>
    <label>GST Type *</label>
    <div class="gst-type-toggle">
      <input type="radio" id="gst-inclusive" name="gstType" value="inclusive" checked>
      <label for="gst-inclusive" class="radio-label">Inclusive</label>
      <input type="radio" id="gst-exclusive" name="gstType" value="exclusive">
      <label for="gst-exclusive" class="radio-label">Exclusive</label>
    </div>
  </div>
  <div>
    <label>GST Percentage %</label>
    <input type="number" id="gst-percentage" name="gstPercentage" value="18" step="0.1" min="0" max="100">
  </div>
</div>
```

### Pricing Summary Card
```html
<div class="pricing-summary-card">
  <div class="pricing-header">💰 Pricing Summary</div>

  <div class="pricing-grid">
    <div class="pricing-item">
      <span class="pricing-label">Discount</span>
      <span class="pricing-value" id="calc-discount">0%</span>
    </div>
    <div class="pricing-item">
      <span class="pricing-label">Base Price</span>
      <span class="pricing-value" id="calc-base">₹0</span>
    </div>
    <div class="pricing-item">
      <span class="pricing-label">GST Amount</span>
      <span class="pricing-value" id="calc-gst">₹0</span>
    </div>
    <div class="pricing-item">
      <span class="pricing-label">Final Price</span>
      <span class="pricing-value final" id="calc-final">₹0</span>
    </div>
    <div class="pricing-item">
      <span class="pricing-label">Profit Margin</span>
      <span class="pricing-value" id="calc-profit">0%</span>
    </div>
    <div class="pricing-item">
      <span class="pricing-label">Profit Amount</span>
      <span class="pricing-value profit" id="calc-profit-amount">₹0</span>
    </div>
  </div>

  <div class="pricing-warnings" id="pricing-warnings"></div>
</div>
```

## 5. CSS Styling

```css
.gst-type-toggle {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 0.5rem;
}

.gst-type-toggle input[type="radio"] {
  display: none;
}

.radio-label {
  padding: 0.6rem 1.2rem;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.85rem;
  transition: all 0.3s;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--cream);
}

.gst-type-toggle input[type="radio"]:checked + .radio-label {
  background: var(--gold);
  color: #fff;
  border-color: var(--gold);
}

.pricing-summary-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 2px solid var(--gold);
  border-radius: 12px;
  padding: 1.5rem;
  margin-top: 1.5rem;
  box-shadow: 0 4px 12px rgba(201,168,76,0.1);
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.pricing-item {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.9rem;
  text-align: center;
  transition: all 0.3s;
}

.pricing-item:hover {
  border-color: var(--gold);
  box-shadow: 0 2px 8px rgba(201,168,76,0.1);
}

.pricing-label {
  display: block;
  font-size: 0.75rem;
  color: var(--ink-light);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 0.5rem;
}

.pricing-value {
  display: block;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--success);
}

.pricing-value.final {
  color: var(--gold);
  font-size: 1.3rem;
}

.pricing-value.profit {
  color: var(--success);
}
```

## 6. JavaScript Calculation Engine

```javascript
function updateCalculations() {
  const mrp = parseFloat(document.getElementById('mrp').value) || 0;
  const discount = parseFloat(document.getElementById('discount-price').value) || 0;
  const cost = parseFloat(document.getElementById('cost-price').value) || 0;
  const gst = parseFloat(document.getElementById('gst-percentage').value) || 0;
  const gstType = document.querySelector('input[name="gstType"]:checked').value || 'inclusive';

  let basePrice, gstAmount, finalPrice;

  if (gstType === 'inclusive') {
    basePrice = gst > 0 ? discount / (1 + gst / 100) : discount;
    gstAmount = discount - basePrice;
    finalPrice = discount;
  } else {
    basePrice = discount;
    gstAmount = (discount * gst) / 100;
    finalPrice = discount + gstAmount;
  }

  basePrice = Math.round(basePrice * 100) / 100;
  gstAmount = Math.round(gstAmount * 100) / 100;
  finalPrice = Math.round(finalPrice * 100) / 100;

  const discountPct = mrp > 0 ? Math.round(((mrp - discount) / mrp) * 100) : 0;
  const profitPct = cost > 0 ? Math.round(((discount - cost) / cost) * 100) : 0;
  const profitAmount = Math.round((discount - cost) * 100) / 100;

  document.getElementById('calc-discount').textContent = discountPct + '%';
  document.getElementById('calc-base').textContent = '₹' + basePrice.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  document.getElementById('calc-gst').textContent = '₹' + gstAmount.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  document.getElementById('calc-final').textContent = '₹' + finalPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  document.getElementById('calc-profit').textContent = profitPct + '%';
  document.getElementById('calc-profit-amount').textContent = '₹' + profitAmount.toLocaleString('en-IN', { maximumFractionDigits: 2 });

  validatePricing(mrp, discount, cost, gst);
}

function validatePricing(mrp, discount, cost, gst) {
  const warnings = document.getElementById('pricing-warnings');
  const warningsList = [];

  if (discount > mrp && mrp > 0) {
    warningsList.push('⚠️ Selling Price cannot exceed MRP');
  }
  if (discount < 0 || mrp < 0 || cost < 0) {
    warningsList.push('⚠️ Prices cannot be negative');
  }
  if (gst > 100) {
    warningsList.push('⚠️ GST cannot exceed 100%');
  }
  if (discount < cost && cost > 0 && discount > 0) {
    warningsList.push('⚠️ Selling Price is below Cost Price - Loss!');
  }

  warnings.innerHTML = warningsList.length > 0
    ? warningsList.map(w => `<div class="warning-item">${w}</div>`).join('')
    : '';
}
```

## 7. Event Listeners Setup

```javascript
document.getElementById('mrp').addEventListener('change', updateCalculations);
document.getElementById('mrp').addEventListener('input', updateCalculations);
document.getElementById('discount-price').addEventListener('change', updateCalculations);
document.getElementById('discount-price').addEventListener('input', updateCalculations);
document.getElementById('cost-price').addEventListener('change', updateCalculations);
document.getElementById('cost-price').addEventListener('input', updateCalculations);
document.getElementById('gst-percentage').addEventListener('change', updateCalculations);
document.getElementById('gst-percentage').addEventListener('input', updateCalculations);
document.getElementById('gst-inclusive').addEventListener('change', updateCalculations);
document.getElementById('gst-exclusive').addEventListener('change', updateCalculations);
```

## 8. Loading Product Data

```javascript
function loadProductData(product) {
  // ... existing loads ...
  document.getElementById('gst-percentage').value = product.gstPercentage || 18;

  const gstType = product.gstType || 'inclusive';
  if (gstType === 'inclusive') {
    document.getElementById('gst-inclusive').checked = true;
  } else {
    document.getElementById('gst-exclusive').checked = true;
  }

  // ... existing updates ...
  updateCalculations();
}
```

---

## Key Formulas

### GST Inclusive
```
Base Price = Selling Price / (1 + GST% / 100)
GST Amount = Selling Price - Base Price
Final Price = Selling Price
```

### GST Exclusive
```
Base Price = Selling Price
GST Amount = (Selling Price × GST%) / 100
Final Price = Selling Price + GST Amount
```

### Common Calculations
```
Discount % = ((MRP - Selling Price) / MRP) × 100
Profit Margin % = ((Selling Price - Cost Price) / Cost Price) × 100
Profit Amount = Selling Price - Cost Price
```

---

## Integration Points

1. **Frontend Form:** Real-time calculations on input change
2. **Backend API:** Receives and validates gstType
3. **Database:** Stores gstType with each product
4. **API Response:** Returns all pricing fields in to_dict()
5. **Admin Panel:** Displays summary card with warnings

---

**Version:** 1.0
**Last Updated:** May 26, 2026
