import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// CSRF helper
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// ── INDEXEDDB OFFLINE STORAGE ──
const DB_NAME = 'MeatFlowOfflineDB';
const DB_VERSION = 1;
const STORE_NAME = 'sales';

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };
    request.onsuccess = (e) => resolve(e.target.result);
    request.onerror = (e) => reject(e.target.error);
  });
}

async function saveOfflineSale(sale) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.add({ ...sale, timestamp: new Date().toISOString() });
    request.onsuccess = () => resolve(true);
    request.onerror = (e) => reject(e.target.error);
  });
}

async function getOfflineSales() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = (e) => reject(e.target.error);
  });
}

async function deleteOfflineSale(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.delete(id);
    request.onsuccess = () => resolve(true);
    request.onerror = (e) => reject(e.target.error);
  });
}

// ── SPEECH RECOGNITION (VOICE COMMANDS) ──
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.lang = 'uz-UZ';
  recognition.interimResults = false;
}

function App() {
  // Navigation & States
  const [isListening, setIsListening] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('');
  const [cachedCustomers, setCachedCustomers] = useState([]);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineCount, setOfflineCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [step, setStep] = useState(1); // 1: Product, 2: Customer, 3: Confirm, 4: Success/Receipt
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [visibleCustomersCount, setVisibleCustomersCount] = useState(10);
  
  // Selection
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null); // null means anonymous
  
  // Weight & Scale states
  const [weight, setWeight] = useState(0.000);
  const [isManualMode, setIsManualMode] = useState(false);
  const [isUsbConnected, setIsUsbConnected] = useState(false);
  const [activeScaleId, setActiveScaleId] = useState("1"); // "1" for Kassa, "2" for Wi-Fi
  
  // Web Serial Refs & States
  const usbPortRef = useRef(null);
  const usbReaderRef = useRef(null);
  const pollingIntervalRef = useRef(null);

  // Numpad modal
  const [numpadOpen, setNumpadOpen] = useState(false);
  const [numpadBuffer, setNumpadBuffer] = useState('');
  const [numpadMode, setNumpadMode] = useState('kg'); // 'kg' or 'sum'

  // Payment & Totals
  const [paymentMethod, setPaymentMethod] = useState('naqd');
  const [quickAmounts, setQuickAmounts] = useState([]);
  const [selectedAmount, setSelectedAmount] = useState(0);
  const [loadingSale, setLoadingSale] = useState(false);
  const [receiptData, setReceiptData] = useState(null);

  // Create customer form
  const [showAddCustomer, setShowAddCustomer] = useState(false);
  const [custFirstName, setCustFirstName] = useState('');
  const [custLastName, setCustLastName] = useState('');
  const [custPhone, setCustPhone] = useState('');
  const [custCustomId, setCustCustomId] = useState('');
  const [custError, setCustError] = useState('');
  const [custDebtLimit, setCustDebtLimit] = useState('1000000');

  // Fetch Products & Customers on Mount
  useEffect(() => {
    fetch('/pos/api/products/')
      .then(res => res.json())
      .then(data => setProducts(data))
      .catch(err => console.error("Error loading products:", err));

    fetch('/pos/api/customers/')
      .then(res => res.json())
      .then(data => setCachedCustomers(data))
      .catch(err => console.error("Error loading cached customers:", err));
  }, []);

  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncOfflineSales();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    checkOfflineCount();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const checkOfflineCount = async () => {
    try {
      const sales = await getOfflineSales();
      setOfflineCount(sales.length);
    } catch (e) {
      console.error(e);
    }
  };

  const syncOfflineSales = async () => {
    if (!navigator.onLine) return;
    const sales = await getOfflineSales();
    if (sales.length === 0) return;

    setSyncing(true);
    let successCount = 0;

    for (let sale of sales) {
      const dbId = sale.id;
      const payload = { ...sale };
      delete payload.id;
      delete payload.timestamp;

      try {
        const res = await fetch('/pos/api/sales/create/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(payload)
        });
        let data;
        try {
          data = await res.json();
        } catch (jsonErr) {
          const textRes = await res.text();
          throw new Error(`Serverdan noto'g'ri javob keldi (Status: ${res.status}): ${textRes.substring(0, 150)}`);
        }

        if (data.status === 'success' || data.sale_id) {
          await deleteOfflineSale(dbId);
          successCount++;
        } else {
          const errorMsg = data.error || data.message || 'Noma\'lum xato';
          if (confirm(`Savdoni sinxronlashda xatolik:\n${errorMsg}\n\nUshbu savdo noto'g'ri ma'lumotlar bilan yozilgan bo'lishi mumkin. Ushbu buzilgan savdoni ro'yxatdan o'chirib yuborishni xohlaysizmi (sinxronizatsiya davom etishi uchun)?`)) {
            await deleteOfflineSale(dbId);
          } else {
            break;
          }
        }
      } catch (e) {
        console.error("Failed to sync offline sale:", e);
        alert(`Offlayn savdoni yuklashda texnik xatolik yuz berdi:\n${e.message || e.toString()}`);
        break;
      }
    }

    setSyncing(false);
    checkOfflineCount();
    if (successCount > 0) {
      alert(`${successCount} ta offline savdo serverga muvaffaqiyatli sinxronlashtirildi!`);
    }
  };

  // Speech Recognition handlers
  useEffect(() => {
    if (!recognition) return;

    recognition.onstart = () => {
      setIsListening(true);
      setVoiceStatus('Tinglanmoqda...');
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = (e) => {
      console.error(e);
      setVoiceStatus('Ovozni eshitishda xato: ' + e.error);
      setIsListening(false);
    };

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      setVoiceStatus(`Tushunilgan matn: "${text}"`);
      
      const result = parseVoiceCommand(text, products, cachedCustomers);
      
      if (result.product) {
        setSelectedProduct(result.product);
        if (result.weight > 0) {
          setWeight(result.weight);
          setIsManualMode(true);
        }
        if (result.customer) {
          setSelectedCustomer(result.customer);
        }
        if (result.paymentMethod) {
          setPaymentMethod(result.paymentMethod);
        }
        setStep(3);
      } else {
        alert(`Ovoz tushunildi: "${text}", lekin mos mahsulot topilmadi!`);
      }
    };
  }, [products, cachedCustomers]);

  const parseVoiceCommand = (text, productsList, customersList) => {
    const cleanText = text.toLowerCase().replace(/['`’]/g, '');
    console.log("Transcribed speech:", cleanText);

    let detectedProduct = null;
    let detectedWeight = 0;
    let detectedCustomer = null;
    let detectedPayment = 'naqd';

    // 1. Detect Product
    for (let p of productsList) {
      const cleanProdName = p.name.toLowerCase().replace(/['`’]/g, '');
      if (cleanText.includes(cleanProdName) || cleanProdName.split(' ').some(word => cleanText.includes(word))) {
        detectedProduct = p;
        break;
      }
    }

    // 2. Detect Weight
    const numberMatches = cleanText.match(/(\d+[\.,]\d+|\d+)/g);
    if (numberMatches) {
      let rawNum = numberMatches[0].replace(',', '.');
      detectedWeight = parseFloat(rawNum);
    }

    if (cleanText.includes('yarim')) {
      if (detectedWeight > 0) {
        detectedWeight += 0.5;
      } else {
        detectedWeight = 0.5;
      }
    }

    // 3. Detect Customer
    for (let c of customersList) {
      const cleanCustName = c.name.toLowerCase().replace(/['`’]/g, '');
      const nameWords = cleanCustName.split(/\s+/);
      if (nameWords.length > 0 && cleanText.includes(nameWords[0])) {
        detectedCustomer = c;
        break;
      }
    }

    // 4. Detect Payment Method
    if (cleanText.includes('qarz') || cleanText.includes('nasiya')) {
      detectedPayment = 'nasiya';
    } else if (cleanText.includes('karta') || cleanText.includes('plastik')) {
      detectedPayment = 'karta';
    } else if (cleanText.includes('qr') || cleanText.includes('kod')) {
      detectedPayment = 'qr';
    }

    return {
      product: detectedProduct,
      weight: detectedWeight,
      customer: detectedCustomer,
      paymentMethod: detectedPayment
    };
  };

  const toggleListening = () => {
    if (!recognition) return;
    if (isListening) {
      recognition.stop();
    } else {
      setVoiceStatus('');
      recognition.start();
    }
  };

  // Poll scale weight if not in manual/USB modes
  useEffect(() => {
    if (isManualMode || isUsbConnected) {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      return;
    }

    pollingIntervalRef.current = setInterval(() => {
      const url = activeScaleId === '2'
        ? 'http://192.168.137.81/pos/api/get-weight/'
        : `/pos/api/get-weight/?scale_id=${activeScaleId}`;

      fetch(url)
        .then(res => res.json())
        .then(data => {
          const v = data.vazn !== undefined ? data.vazn : data.weight;
          if (v !== undefined) {
            setWeight(parseFloat(v));
          }
        })
        .catch(() => {});
    }, 500);

    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, [isManualMode, isUsbConnected, activeScaleId]);

  // Search Customers
  useEffect(() => {
    if (!searchQuery.trim()) {
      setCustomers([]);
      return;
    }
    setVisibleCustomersCount(10);
    const delayDebounce = setTimeout(() => {
      fetch(`/pos/api/customers/?q=${searchQuery}`)
        .then(res => res.json())
        .then(data => setCustomers(data))
        .catch(err => console.error("Customer search error:", err));
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  const sendTelegramReminder = (id, name, debt) => {
    const formattedDebt = Math.round(debt).toLocaleString();
    const message = `Assalomu alaykum, hurmatli ${name}. Do'konimizdan olingan ${formattedDebt} so'mlik nasiya muddati o'tdi. Iloji bo'lsa, to'lovni amalga oshirishingizni so'raymiz. Rahmat!`;
    
    if (window.confirm(`Quyidagi eslatmani mijozga yuborasizmi?\n\n"${message}"`)) {
      fetch(`/pos/customer-chat/send/${id}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ message: message })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert(`Telegram eslatma muvaffaqiyatli yuborildi!\n(Mijoz chat logida saqlandi)`);
        } else {
          alert("Xatolik yuz berdi: " + data.message);
        }
      })
      .catch(err => {
        console.error("Error sending telegram reminder:", err);
        alert("Eslatma yuborishda xatolik yuz berdi.");
      });
    }
  };

  // Generate Quick Amounts on confirming step
  useEffect(() => {
    if (step === 3 && selectedProduct && weight > 0) {
      const price = selectedProduct.price_per_kg;
      const exact = Math.round(weight * price);
      const amounts = new Set();
      amounts.add(exact);

      [5000, 10000].forEach(stepSize => {
        const down = Math.floor(exact / stepSize) * stepSize;
        const down2 = down - stepSize;
        if (down > 0 && down !== exact) amounts.add(down);
        if (down2 > 0 && down2 !== exact) amounts.add(down2);
      });

      const sorted = [...amounts].sort((a, b) => a - b);
      setQuickAmounts(sorted);
      setSelectedAmount(exact);
    }
  }, [step, selectedProduct, weight]);

  // Web Serial USB connection
  const connectUSBScale = async () => {
    if (!("serial" in navigator)) {
      alert("Kechirasiz, brauzeringiz Web Serial API-ni qo'llab-quvvatlamaydi. Iltimos, Google Chrome yoki Microsoft Edge brauzerini ishlating!");
      return;
    }

    try {
      const port = await navigator.serial.requestPort();
      await port.open({ baudRate: 115200 });
      
      usbPortRef.current = port;
      setIsUsbConnected(true);
      setIsManualMode(false);
      
      // Stop HTTP Polling
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

      readSerialStream(port);
    } catch (err) {
      console.error("USB scale connection error:", err);
      alert("Tarozi ulana olmadi: " + err.message);
      disconnectUSBScale();
    }
  };

  const readSerialStream = async (port) => {
    const textDecoder = new TextDecoderStream();
    const readableStreamClosed = port.readable.pipeTo(textDecoder.writable);
    const reader = textDecoder.readable.getReader();
    usbReaderRef.current = reader;

    let buffer = '';
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += value;
        let lines = buffer.split('\n');
        buffer = lines.pop();
        
        for (let line of lines) {
          line = line.trim();
          if (line.includes('VAZN:')) {
            const match = line.match(/VAZN:([\d\.-]+)/);
            if (match) {
              const wVal = parseFloat(match[1]);
              if (!isNaN(wVal)) {
                setWeight(wVal);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Serial stream read error:", err);
    } finally {
      reader.releaseLock();
    }
  };

  const disconnectUSBScale = async () => {
    setIsUsbConnected(false);
    if (usbReaderRef.current) {
      try {
        await usbReaderRef.current.cancel();
      } catch (e) {}
      usbReaderRef.current = null;
    }
    if (usbPortRef.current) {
      try {
        await usbPortRef.current.close();
      } catch (e) {}
      usbPortRef.current = null;
    }
  };

  const tareWiFiScale = () => {
    fetch('http://192.168.137.81/pos/api/tare/')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert("Wi-Fi tarozi muvaffaqiyatli nollatildi!");
        } else {
          alert("Tarozi javob bermadi yoki xatolik yuz berdi.");
        }
      })
      .catch(err => {
        console.error("Tare WiFi Scale error:", err);
        alert("Wi-Fi taroziga ulanib bo'lmadi (Tarmoq yoki CORS xatosi).");
      });
  };

  const handleScaleTabChange = (scaleId) => {
    setActiveScaleId(scaleId);
    disconnectUSBScale();
    setIsManualMode(false);
  };

  // Numpad Handlers
  const handleOpenNumpad = () => {
    setNumpadMode('kg');
    setNumpadBuffer(weight > 0 ? weight.toString() : '');
    setNumpadOpen(true);
    setIsManualMode(true);
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    disconnectUSBScale();
  };

  const handleNumpadKey = (key) => {
    if (key === 'del') {
      setNumpadBuffer(prev => prev.slice(0, -1));
    } else if (key === '.') {
      if (numpadMode === 'kg' && !numpadBuffer.includes('.')) {
        setNumpadBuffer(prev => prev + '.');
      }
    } else {
      if (numpadMode === 'kg') {
        if (numpadBuffer === '0') setNumpadBuffer(key);
        else setNumpadBuffer(prev => prev + key);
      } else {
        if (numpadBuffer === '' || numpadBuffer === '0') setNumpadBuffer(key);
        else setNumpadBuffer(prev => prev + key);
      }
    }
  };

  const handleNumpadConfirm = () => {
    if (numpadMode === 'kg') {
      const val = parseFloat(numpadBuffer);
      if (!isNaN(val) && val >= 0) {
        setWeight(val);
      }
    } else {
      const sumVal = parseInt(numpadBuffer) || 0;
      if (selectedProduct && sumVal > 0) {
        const price = selectedProduct.price_per_kg;
        const calculatedKg = (sumVal / price);
        setWeight(parseFloat(calculatedKg.toFixed(3)));
        setSelectedAmount(sumVal);
      }
    }
    setNumpadOpen(false);
  };

  // Select flow
  const handleSelectProduct = (prod) => {
    setSelectedProduct(prod);
    setStep(2);
  };

  const handleConfirmCustomer = (cust) => {
    setSelectedCustomer(cust);
    setStep(3);
  };

  // Create new customer
  const generateAutoId = () => {
    if (custPhone) {
      const cleanPhone = custPhone.replace(/\D/g, '');
      setCustCustomId("M-" + cleanPhone.slice(-4));
    } else {
      setCustCustomId("M-" + Math.floor(1000 + Math.random() * 9000));
    }
  };

  const handleSaveCustomer = () => {
    if (!custFirstName || !custPhone) {
      setCustError("Ism va Telefon raqami majburiy!");
      return;
    }
    setCustError('');
    
    const fileInput = document.getElementById('new-cust-image');
    const imageFile = fileInput && fileInput.files ? fileInput.files[0] : null;

    const formData = new FormData();
    formData.append('first_name', custFirstName);
    formData.append('last_name', custLastName || '');
    formData.append('phone', custPhone);
    formData.append('custom_id', custCustomId || ("M-" + Math.floor(1000 + Math.random() * 9000)));
    formData.append('debt_limit', custDebtLimit || '1000000');
    if (imageFile) {
      formData.append('image', imageFile);
    }

    fetch('/pos/api/customers/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setCustError(data.error);
        } else {
          // Success
          setSelectedCustomer({
            id: data.id,
            name: data.name,
            custom_id: data.custom_id,
            phone: data.phone,
            bonus_points: data.bonus_points || 0,
            debt_amount: data.debt_amount || 0,
            debt_limit: data.debt_limit || 1000000,
            credit_score: data.credit_score || 'B (Yangi)'
          });
          setShowAddCustomer(false);
          // reset form
          setCustFirstName('');
          setCustLastName('');
          setCustPhone('');
          setCustCustomId('');
          setCustDebtLimit('1000000');
          if (fileInput) fileInput.value = '';
          setStep(3);
        }
      })
      .catch(err => {
        setCustError("Mijozni saqlashda xatolik.");
      });
  };

  // Submit Sale to Backend
  const handleSubmitSale = () => {
    if (!selectedProduct) {
      alert("Mahsulot tanlanmagan!");
      return;
    }
    if (weight <= 0) {
      alert("Vazn noto'g'ri!");
      return;
    }

    setLoadingSale(true);

    const totalAmount = weight * parseFloat(selectedProduct.price_per_kg);
    const finalPaid = paymentMethod === 'nasiya' ? 0 : selectedAmount;
    let discountAmount = totalAmount - selectedAmount;
    if (discountAmount < 0) discountAmount = 0;

    let bonusUsed = 0;
    let debtAdded = paymentMethod === 'nasiya' ? selectedAmount : 0;

    if (selectedCustomer && paymentMethod !== 'nasiya' && discountAmount > 0) {
      const available = selectedCustomer.bonus_points || 0;
      if (available >= discountAmount) {
        bonusUsed = discountAmount;
      } else {
        bonusUsed = available;
        debtAdded = discountAmount - available;
      }
    }

    const payload = {
      customer_id: selectedCustomer ? selectedCustomer.id : null,
      payment_method: paymentMethod,
      total_amount: Math.round(totalAmount),
      discount_amount: Math.round(discountAmount),
      bonus_used: Math.round(bonusUsed),
      debt_added: Math.round(debtAdded),
      final_paid: Math.round(finalPaid),
      items: [
        {
          product_id: selectedProduct.id,
          weight: weight
        }
      ]
    };

    // If offline, save directly to IndexedDB
    if (!navigator.onLine) {
      saveOfflineSale(payload)
        .then(() => {
          setLoadingSale(false);
          checkOfflineCount();
          setReceiptData({
            sale_id: "OFFLINE-" + Math.floor(1000 + Math.random() * 9000),
            status: "success"
          });
          setStep(4);
        })
        .catch(err => {
          setLoadingSale(false);
          alert("Offline saqlashda xato: " + err.message);
        });
      return;
    }

    fetch('/pos/api/sales/create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(payload)
    })
      .then(res => {
        if (!res.ok) throw new Error("Server error");
        return res.json();
      })
      .then(data => {
        setLoadingSale(false);
        if (data.error) {
          alert("Xatolik: " + data.error);
        } else {
          // Success
          setReceiptData(data);
          setStep(4);
        }
      })
      .catch(err => {
        console.warn("Network error, falling back to offline IndexedDB saving:", err);
        saveOfflineSale(payload)
          .then(() => {
            setLoadingSale(false);
            checkOfflineCount();
            setReceiptData({
              sale_id: "OFFLINE-" + Math.floor(1000 + Math.random() * 9000),
              status: "success"
            });
            setStep(4);
          })
          .catch(e => {
            setLoadingSale(false);
            alert("Savdo saqlanmadi (Tarmoq xatosi va offline saqlab bo'lmadi).");
          });
      });
  };

  const resetTerminal = () => {
    setSelectedProduct(null);
    setSelectedCustomer(null);
    setWeight(0.000);
    setPaymentMethod('naqd');
    setReceiptData(null);
    setSearchQuery('');
    setIsManualMode(false);
    setStep(1);
    // Restart polling
    handleScaleTabChange("1");
  };

  return (
    <div className="pos-shell">
      {/* ════ LEFT PANEL ════ */}
      <div className="left-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div className="app-label" style={{ margin: 0 }}>MeatFlow POS</div>
          {recognition && (
            <button 
              onClick={toggleListening}
              className={`mic-btn ${isListening ? 'listening' : ''}`}
              title="Ovozli AI boshqaruv"
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                border: 'none',
                background: isListening ? '#DC3545' : 'rgba(255,255,255,0.1)',
                color: '#fff',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '18px',
                transition: 'all 0.2s',
                boxShadow: isListening ? '0 0 12px #DC3545' : 'none'
              }}
            >
              🎤
            </button>
          )}
        </div>

        {voiceStatus && (
          <div style={{ fontSize: '11px', color: '#D4A853', background: 'rgba(212,168,83,0.1)', border: '1px solid rgba(212,168,83,0.2)', padding: '8px 12px', borderRadius: '10px', marginBottom: '15px', textAlign: 'left', lineHeight: '1.4' }}>
            {voiceStatus}
          </div>
        )}

        {/* Connection status badge */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', padding: '10px 14px', background: 'rgba(255,255,255,0.06)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isOnline ? '#81EFBB' : '#DC3545', display: 'inline-block' }}></span>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: isOnline ? '#81EFBB' : '#FFAFAF', textTransform: 'uppercase' }}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          {offlineCount > 0 && (
            <button 
              onClick={syncOfflineSales} 
              disabled={syncing}
              style={{
                background: '#D4A853',
                border: 'none',
                borderRadius: '8px',
                padding: '4px 10px',
                fontSize: '11px',
                fontWeight: 'bold',
                color: '#1A1A2E',
                cursor: 'pointer',
                transition: 'opacity 0.2s'
              }}
            >
              {syncing ? 'Sinxron...' : `Sync (${offlineCount})`}
            </button>
          )}
        </div>

        <div className="scale-tabs" style={{ display: 'flex', gap: '6px', marginBottom: '20px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button 
            className={`scale-tab ${activeScaleId === '1' && !isUsbConnected ? 'on' : ''}`}
            onClick={() => handleScaleTabChange('1')}
          >
            ⚡ Kassa
          </button>
          <button 
            className={`scale-tab ${activeScaleId === '2' && !isUsbConnected ? 'on' : ''}`}
            onClick={() => handleScaleTabChange('2')}
          >
            📶 Wi-Fi
          </button>
          <button 
            id="btn-usb-connect"
            className={`scale-tab ${isUsbConnected ? 'on' : ''}`}
            onClick={connectUSBScale}
          >
            {isUsbConnected ? '✅ USB Ulandi' : '🔌 USB Ulanish'}
          </button>
          {activeScaleId === '2' && !isUsbConnected && (
            <button
              onClick={tareWiFiScale}
              style={{
                padding: '6px 12px',
                borderRadius: '10px',
                border: 'none',
                background: '#dc3545',
                color: '#FFFFFF',
                fontWeight: 'bold',
                fontSize: '11px',
                cursor: 'pointer',
                marginLeft: 'auto',
                boxShadow: '0 2px 6px rgba(220,53,69,0.2)'
              }}
            >
              🔄 Tarani nollash
            </button>
          )}
        </div>

        <div 
          className={`weight-block ${isManualMode ? 'manual-on' : ''}`} 
          onClick={handleOpenNumpad}
          style={{ cursor: 'pointer' }}
        >
          <div className="weight-label-row">
            <span className="weight-lbl">Vazn</span>
            <span className={`weight-status ${isManualMode ? 'manual' : ''}`}>
              {isManualMode ? 'MANUAL' : isUsbConnected ? 'USB VAZN' : 'AUTO'}
            </span>
          </div>
          <div className="weight-val">
            <span>{weight.toFixed(3)}</span>
            <small>kg</small>
          </div>
          <div className="numpad-hint">▤ kiritish</div>
        </div>

        <div className="prod-strip">
          <div className="prod-strip-lbl">Mahsulot</div>
          <div className={`prod-strip-val ${!selectedProduct ? 'none' : ''}`}>
            {selectedProduct ? selectedProduct.name : 'Tanlanmagan'}
          </div>
        </div>

        <div className="step-dots">
          <div className={`step-dot ${step === 1 ? 'active' : step > 1 ? 'done' : ''}`}></div>
          <div className={`step-dot ${step === 2 ? 'active' : step > 2 ? 'done' : ''}`}></div>
          <div className={`step-dot ${step === 3 ? 'active' : step > 3 ? 'done' : ''}`}></div>
        </div>
      </div>

      {/* ════ RIGHT PANEL ════ */}
      <div className="right-panel">
        
        {/* STEP 1: Products */}
        {step === 1 && (
          <div className="fade-up">
            <div className="step-title">Mahsulotlar</div>
            <div className="step-sub">Sotish uchun mahsulotni tanlang</div>
            <div className="prod-grid">
              {products.map(p => (
                <button key={p.id} className="prod-btn" onClick={() => handleSelectProduct(p)}>
                  <div style={{ position: 'relative', width: '100%', height: '140px', borderRadius: '10px', overflow: 'hidden' }}>
                    <img src={p.image} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.05) 55%, transparent 100%)' }}></div>
                    <div style={{ position: 'absolute', bottom: '10px', left: '12px', right: '12px', textAlign: 'left' }}>
                      <div className="prod-btn-name" style={{ color: '#fff' }}>{p.name}</div>
                      <div className="prod-btn-price" style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px' }}>
                        {parseFloat(p.price_per_kg).toLocaleString('fr-FR')} so'm / kg
                      </div>
                    </div>
                  </div>
                </button>
              ))}
              {products.length === 0 && (
                <div className="prod-empty">Faol mahsulotlar topilmadi</div>
              )}
            </div>
          </div>
        )}

        {/* STEP 2: Customer Search / Selection */}
        {step === 2 && (
          <div className="fade-up">
            <div className="step-title">Mijoz</div>
            <div className="step-sub">Mijozni qidiring yoki yangi qo'shing</div>
            
            <div className="search-row" style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
              <input 
                type="text" 
                className="search-field"
                placeholder="Ism yoki telefon..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoComplete="off"
                style={{ flex: 1, padding: '12px', borderRadius: '12px', border: '1.5px solid rgba(0,0,0,0.07)', outline: 'none' }}
              />
              <button 
                className="btn-new-cust"
                onClick={() => setShowAddCustomer(true)}
                style={{ width: '48px', height: '48px', borderRadius: '12px', background: '#1B6B4A', color: '#fff', border: 'none', fontSize: '20px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                +
              </button>
            </div>

            <div className="results-list" style={{ marginBottom: '20px', maxHeight: '300px', overflowY: 'auto' }}>
              {customers.slice(0, visibleCustomersCount).map(c => (
                <div 
                  key={c.id} 
                  style={{ background: '#fff', border: '1.5px solid rgba(0,0,0,0.07)', borderRadius: '14px', padding: '12px 14px', marginBottom: '6px', cursor: 'pointer' }}
                  onClick={() => handleConfirmCustomer(c)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', textAlign: 'left' }}>
                      <img 
                        src={c.image} 
                        alt={c.name} 
                        style={{ width: '40px', height: '40px', borderRadius: '50%', objectFit: 'cover', border: '1px solid rgba(0,0,0,0.08)' }} 
                      />
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className="cust-name" style={{ fontWeight: 'bold' }}>{c.name}</span>
                          <div style={{ display: 'inline-flex', gap: '5px' }} onClick={(e) => e.stopPropagation()}>
                            {/* Edit */}
                            <a 
                              href={"/pos/customers/?search=" + c.custom_id} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              title="Tahrirlash"
                              style={{ 
                                display: 'inline-flex', 
                                width: '32px', 
                                height: '32px', 
                                borderRadius: '10px', 
                                border: '1px solid rgba(0,0,0,0.08)', 
                                justifyContent: 'center', 
                                alignItems: 'center', 
                                color: '#B06000', 
                                backgroundColor: 'rgba(212,168,83,0.08)',
                                textDecoration: 'none'
                              }}
                            >
                              <i className="bi bi-pencil-fill" style={{ fontSize: '13px' }}></i>
                            </a>
                          </div>
                        </div>
                        <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <span>ID: {c.custom_id}</span>
                          {c.phone && <span>· {c.phone}</span>}
                          {c.credit_score && (
                            <span style={{ 
                              background: c.credit_score.startsWith('A') ? '#E6F4EA' : c.credit_score.startsWith('B') ? '#E8F0FE' : c.credit_score.startsWith('C') ? '#FEF7E0' : '#FCE8E6', 
                              color: c.credit_score.startsWith('A') ? '#137333' : c.credit_score.startsWith('B') ? '#1A73E8' : c.credit_score.startsWith('C') ? '#B06000' : '#C5221F', 
                              padding: '1px 6px', 
                              borderRadius: '4px', 
                              fontSize: '10px', 
                              fontWeight: '800' 
                            }}>
                              AI Skoring: {c.credit_score}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                      {c.debt_amount > 0 && (
                        <span className="debt-pill" style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', padding: '4px 10px', color: '#DC3545', fontSize: '11px', fontWeight: 'bold' }}>
                          Qarz: {parseFloat(c.debt_amount).toLocaleString('fr-FR')} so'm
                        </span>
                      )}
                      {c.debt_limit && (
                        <span style={{ fontSize: '10px', color: '#9CA3AF' }}>
                          Limit: {parseFloat(c.debt_limit).toLocaleString('fr-FR')} so'm
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {customers.length > visibleCustomersCount && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setVisibleCustomersCount(prev => prev + 10); }} 
                  style={{ width: '100%', padding: '10px', borderRadius: '10px', background: 'transparent', border: '1.5px solid #1B6B4A', color: '#1B6B4A', fontWeight: 'bold', cursor: 'pointer', margin: '10px 0' }}
                >
                  Yana yuklash...
                </button>
              )}
              {searchQuery.trim() && customers.length === 0 && (
                <div style={{ padding: '20px', textAlign: 'center', color: '#9CA3AF' }}>Mijoz topilmadi</div>
              )}
            </div>

            <button 
              className="btn-cash" 
              onClick={() => handleConfirmCustomer(null)}
              style={{ width: '100%', padding: '14px', background: '#F5F1EB', border: '1.5px solid rgba(0,0,0,0.08)', borderRadius: '14px', color: '#1A1A2E', fontWeight: 'bold', cursor: 'pointer', marginBottom: '10px' }}
            >
              Mijozsiz — Naqd pul
            </button>
            
            <button 
              className="btn-back" 
              onClick={() => setStep(1)}
              style={{ background: 'transparent', border: 'none', color: '#6B7280', fontWeight: 'bold', cursor: 'pointer' }}
            >
              ← Orqaga
            </button>
          </div>
        )}

        {/* STEP 3: Confirm & Payment */}
        {step === 3 && (
          <div className="fade-up">
            <div className="step-title">Tasdiqlash</div>
            <div className="step-sub">Savdo ma'lumotlarini tekshiring</div>

            <div className="confirm-cards" style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
              <div className="confirm-card" style={{ flex: 1, background: '#F8F6F2', border: '1.5px solid rgba(0,0,0,0.07)', borderRadius: '14px', padding: '16px', textAlign: 'left' }}>
                <div className="confirm-card-lbl" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold' }}>Xaridor</div>
                <div className="confirm-card-val" style={{ fontSize: '18px', fontWeight: '800', marginTop: '4px' }}>
                  {selectedCustomer ? selectedCustomer.name : 'Nomalum xaridor'}
                </div>
              </div>
              <div className="confirm-card" style={{ flex: 1, background: '#F8F6F2', border: '1.5px solid rgba(0,0,0,0.07)', borderRadius: '14px', padding: '16px', textAlign: 'left' }}>
                <div className="confirm-card-lbl" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold' }}>Vazn</div>
                <div className="confirm-card-val" style={{ fontSize: '18px', fontWeight: '800', marginTop: '4px' }}>
                  {weight.toFixed(3)} kg
                </div>
              </div>
            </div>

            {/* Quick Amounts Grid */}
            <div className="quick-amounts-wrap" style={{ marginBottom: '20px', textAlign: 'left' }}>
              <span className="quick-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                Summa tanlang
              </span>
              <div className="quick-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: '8px' }}>
                {quickAmounts.map(amt => (
                  <button 
                    key={amt} 
                    className={`quick-btn ${selectedAmount === amt ? 'selected exact' : ''}`}
                    onClick={() => setSelectedAmount(amt)}
                    style={{
                      padding: '10px',
                      borderRadius: '10px',
                      border: '1.5px solid rgba(0,0,0,0.07)',
                      background: selectedAmount === amt ? '#1B6B4A' : '#fff',
                      color: selectedAmount === amt ? '#fff' : '#1A1A2E',
                      fontWeight: 'bold',
                      cursor: 'pointer'
                    }}
                  >
                    {amt.toLocaleString('fr-FR')} so'm
                  </button>
                ))}
              </div>
            </div>

            {/* Payment Options */}
            <div style={{ textAlign: 'left', marginBottom: '25px' }}>
              <span className="pay-select-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                To'lov turi
              </span>
              <div className="pay-options" style={{ display: 'flex', gap: '8px' }}>
                {['naqd', 'karta', 'qr', 'nasiya'].map(method => (
                  <button 
                    key={method}
                    className={`pay-opt ${paymentMethod === method ? 'selected' : ''}`}
                    onClick={() => setPaymentMethod(method)}
                    style={{
                      flex: 1,
                      padding: '12px',
                      borderRadius: '12px',
                      border: '1.5px solid rgba(0,0,0,0.07)',
                      background: paymentMethod === method ? 'linear-gradient(135deg, #1B6B4A, #2D9B6E)' : '#fff',
                      color: paymentMethod === method ? '#fff' : '#1A1A2E',
                      fontWeight: 'bold',
                      cursor: 'pointer'
                    }}
                  >
                    {method === 'naqd' ? '💵 Naqd' : method === 'karta' ? '💳 Karta' : method === 'qr' ? '📱 QR' : '📋 Nasiya'}
                  </button>
                ))}
              </div>
            </div>

            {paymentMethod === 'nasiya' && selectedCustomer && (
              <div style={{ 
                marginBottom: '20px', 
                padding: '12px 14px', 
                borderRadius: '12px', 
                background: (parseFloat(selectedCustomer.debt_amount) + selectedAmount) > parseFloat(selectedCustomer.debt_limit) ? '#FCE8E6' : 'rgba(27,107,74,0.06)', 
                border: `1.5px solid ${(parseFloat(selectedCustomer.debt_amount) + selectedAmount) > parseFloat(selectedCustomer.debt_limit) ? '#DC3545' : 'rgba(27,107,74,0.15)'}`, 
                color: (parseFloat(selectedCustomer.debt_amount) + selectedAmount) > parseFloat(selectedCustomer.debt_limit) ? '#C5221F' : '#137333', 
                fontSize: '12px', 
                textAlign: 'left', 
                fontWeight: 'bold',
                lineHeight: '1.4'
              }}>
                {(parseFloat(selectedCustomer.debt_amount) + selectedAmount) > parseFloat(selectedCustomer.debt_limit) ? (
                  <span>
                    ⚠️ Kredit limiti oshib ketadi! Joriy qarz: {parseFloat(selectedCustomer.debt_amount).toLocaleString('fr-FR')} so'm, Limiti: {parseFloat(selectedCustomer.debt_limit).toLocaleString('fr-FR')} so'm.
                  </span>
                ) : (
                  <span>
                    ✅ Kredit limit yetarli. Joriy qarz: {parseFloat(selectedCustomer.debt_amount).toLocaleString('fr-FR')} so'm, Limiti: {parseFloat(selectedCustomer.debt_limit).toLocaleString('fr-FR')} so'm.
                  </span>
                )}
              </div>
            )}

            <button 
              className="btn-confirm" 
              onClick={handleSubmitSale}
              disabled={loadingSale}
              style={{ width: '100%', padding: '16px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '14px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', marginBottom: '15px', boxShadow: '0 4px 12px rgba(27,107,74,0.2)' }}
            >
              {loadingSale ? 'Saqlanmoqda...' : 'Savdoni Tasdiqlash'}
            </button>

            <button 
              className="btn-back" 
              onClick={() => setStep(2)}
              style={{ background: 'transparent', border: 'none', color: '#6B7280', fontWeight: 'bold', cursor: 'pointer' }}
            >
              ← Orqaga
            </button>
          </div>
        )}

        {/* STEP 4: Success / Receipt display */}
        {step === 4 && receiptData && (
          <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div className="step-title" style={{ color: '#1B6B4A' }}>✅ Savdo Muvaffaqiyatli Saqlandi!</div>
            <div className="step-sub">Elektron chek mijoz profiliga va chatga yuborildi</div>

            {/* Receipt Preview */}
            <div 
              style={{
                fontFamily: 'Courier New, monospace',
                background: '#fff',
                border: '1px solid #ccc',
                padding: '20px',
                borderRadius: '12px',
                width: '100%',
                maxWidth: '360px',
                textAlign: 'left',
                color: '#111',
                boxShadow: '0 8px 24px rgba(0,0,0,0.06)',
                marginBottom: '20px'
              }}
            >
              <div style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '18px', marginBottom: '10px', color: '#1b5e20' }}>
                BAXMAL MEAT
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '12px', textAlign: 'center' }}>
                Savdo ID: #{receiptData.sale_id}
              </div>
              <div style={{ borderTop: '2px dashed #333', marginBottom: '10px' }}></div>
              
              {/* Items */}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginBottom: '6px' }}>
                <span>• {selectedProduct ? selectedProduct.name : 'Go\'sht'} ({weight.toFixed(3)} kg)</span>
                <span style={{ fontWeight: 'bold' }}>{Math.round(selectedAmount).toLocaleString('fr-FR')} so'm</span>
              </div>
              
              <div style={{ borderTop: '2px dashed #333', marginTop: '10px', paddingTop: '8px' }}></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', fontWeight: 'bold', marginBottom: '6px' }}>
                <span>JAMI:</span>
                <span>{Math.round(selectedAmount).toLocaleString('fr-FR')} so'm</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#555', marginBottom: '10px' }}>
                <span>To'lov turi:</span>
                <span style={{ textTransform: 'capitalize' }}>
                  {paymentMethod === 'naqd' ? 'Naqd Pul' : paymentMethod === 'karta' ? 'Plastik Karta' : paymentMethod === 'qr' ? 'TBC QR' : 'Nasiya (Qarz)'}
                </span>
              </div>

              <div style={{ borderTop: '1px solid #eee', paddingTop: '8px', fontSize: '12px', textAlign: 'center', color: '#6B7280' }}>
                Sog'lom go'sht — barakali xarid! Rahmat!
              </div>
            </div>

            <button 
              className="btn-confirm" 
              onClick={resetTerminal}
              style={{ width: '100%', maxWidth: '360px', padding: '14px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '14px', fontSize: '15px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Yangi Savdo Boshlash
            </button>
          </div>
        )}

      </div>

      {/* ════════════ VAZN NUMPAD MODAL ════════════ */}
      {numpadOpen && (
        <div className="numpad-overlay open">
          <div className="numpad-box" style={{ background: '#fff', padding: '20px', borderRadius: '24px', width: '320px', boxShadow: '0 10px 40px rgba(0,0,0,0.15)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
              <span style={{ fontWeight: 'bold', color: '#1A1A2E' }}>Klaviatura orqali kiritish</span>
              <button onClick={() => setNumpadOpen(false)} style={{ background: 'transparent', border: 'none', fontSize: '18px', cursor: 'pointer', color: '#9CA3AF' }}>✕</button>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginBottom: '15px' }}>
              <button 
                id="mode-kg"
                style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: numpadMode === 'kg' ? '#1B6B4A' : '#transparent', color: numpadMode === 'kg' ? '#fff' : '#6B7280', fontWeight: 'bold', cursor: 'pointer' }}
                onClick={() => { setNumpadMode('kg'); setNumpadBuffer(''); }}
              >
                Vazn (kg)
              </button>
              <button 
                id="mode-sum"
                style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: numpadMode === 'sum' ? '#1B6B4A' : '#transparent', color: numpadMode === 'sum' ? '#fff' : '#6B7280', fontWeight: 'bold', cursor: 'pointer' }}
                onClick={() => { setNumpadMode('sum'); setNumpadBuffer(''); }}
              >
                Summa (so'm)
              </button>
            </div>

            <div style={{ background: '#F8F6F2', padding: '16px', borderRadius: '14px', textAlign: 'right', marginBottom: '15px' }}>
              <span id="numpadDisplay" style={{ fontSize: '32px', fontWeight: '800', color: '#1A1A2E' }}>
                {numpadMode === 'kg' ? (numpadBuffer || "0") : (parseInt(numpadBuffer) || 0).toLocaleString('fr-FR')}
              </span>
              <small id="numpadUnit" style={{ display: 'block', fontSize: '10px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginTop: '4px' }}>
                {numpadMode === 'kg' ? 'kilogramm' : "so'm"}
              </small>
            </div>

            <div className="numpad-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '15px' }}>
              {['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'del'].map(key => (
                <button 
                  key={key}
                  onClick={() => handleNumpadKey(key)}
                  disabled={key === '.' && numpadMode !== 'kg'}
                  style={{
                    padding: '16px 0',
                    fontSize: '18px',
                    fontWeight: 'bold',
                    borderRadius: '12px',
                    border: '1.5px solid rgba(0,0,0,0.06)',
                    background: '#F8F6F2',
                    color: '#1A1A2E',
                    cursor: 'pointer',
                    opacity: (key === '.' && numpadMode !== 'kg') ? 0.3 : 1
                  }}
                >
                  {key === 'del' ? '⌫' : key}
                </button>
              ))}
            </div>

            <button 
              onClick={handleNumpadConfirm}
              style={{ width: '100%', padding: '14px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Kiritish
            </button>
          </div>
        </div>
      )}

      {/* ════════════ ADD CUSTOMER MODAL ════════════ */}
      {showAddCustomer && (
        <div className="numpad-overlay open">
          <div className="numpad-box" style={{ background: '#fff', padding: '24px', borderRadius: '24px', width: '340px', boxShadow: '0 10px 40px rgba(0,0,0,0.15)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
              <span className="modal-title" style={{ fontWeight: 'bold', color: '#1A1A2E' }}>Yangi mijoz qo'shish</span>
              <button onClick={() => setShowAddCustomer(false)} style={{ background: 'transparent', border: 'none', fontSize: '18px', cursor: 'pointer', color: '#9CA3AF' }}>✕</button>
            </div>

            {custError && (
              <div style={{ color: '#DC3545', fontSize: '13px', fontWeight: 'bold', marginBottom: '10px', textAlign: 'left' }}>
                {custError}
              </div>
            )}

            <div style={{ textAlign: 'left', marginBottom: '12px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Ismi *</label>
              <input 
                type="text" 
                className="mf-input" 
                placeholder="Asliddin"
                value={custFirstName}
                onChange={(e) => setCustFirstName(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none' }}
              />
            </div>
            
            <div style={{ textAlign: 'left', marginBottom: '12px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Familiyasi</label>
              <input 
                type="text" 
                className="mf-input" 
                placeholder="Karimov"
                value={custLastName}
                onChange={(e) => setCustLastName(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none' }}
              />
            </div>

            <div style={{ textAlign: 'left', marginBottom: '12px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Telefon *</label>
              <input 
                type="text" 
                className="mf-input" 
                placeholder="991234567"
                value={custPhone}
                onChange={(e) => setCustPhone(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none' }}
              />
            </div>

            <div style={{ textAlign: 'left', marginBottom: '12px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Rasm (ixtiyoriy)</label>
              <input 
                type="file" 
                id="new-cust-image"
                className="mf-input" 
                accept="image/*"
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ textAlign: 'left', marginBottom: '20px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Mijoz ID *</label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input 
                  type="text" 
                  className="mf-input" 
                  placeholder="Masalan: 01"
                  value={custCustomId}
                  onChange={(e) => setCustCustomId(e.target.value)}
                  style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none' }}
                />
                <button 
                  className="btn-auto"
                  onClick={generateAutoId}
                  style={{ padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.08)', background: '#F5F1EB', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold', color: '#6B7280' }}
                >
                  AVTO
                </button>
              </div>
            </div>

            <div style={{ textAlign: 'left', marginBottom: '20px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Kredit Limiti (so'm)</label>
              <input 
                type="number" 
                className="mf-input" 
                placeholder="1000000"
                value={custDebtLimit}
                onChange={(e) => setCustDebtLimit(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none', boxSizing: 'border-box' }}
              />
            </div>

            <button 
              className="btn-save-cust" 
              onClick={handleSaveCustomer}
              style={{ width: '100%', padding: '14px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Saqlash va Tanlash
            </button>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
