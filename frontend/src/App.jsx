import React, { useState, useEffect, useRef } from 'react';
import * as faceapi from '@vladmandic/face-api';
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
  const [splitNaqd, setSplitNaqd] = useState(0);
  const [splitKarta, setSplitKarta] = useState(0);
  const [splitQr, setSplitQr] = useState(0);
  const [splitNasiya, setSplitNasiya] = useState(0);
  const [quickAmounts, setQuickAmounts] = useState([]);
  const [selectedAmount, setSelectedAmount] = useState(0);
  const [loadingSale, setLoadingSale] = useState(false);
  const [receiptData, setReceiptData] = useState(null);

  // Shift & Z-Report states
  const [shiftData, setShiftData] = useState({ is_open: false, expected_cash: 0 });
  const [shiftModalOpen, setShiftModalOpen] = useState(false);
  const [shiftOpeningCash, setShiftOpeningCash] = useState('0');
  const [shiftActualCash, setShiftActualCash] = useState('');
  const [shiftNotes, setShiftNotes] = useState('');
  const [zReportData, setZReportData] = useState(null);
  const [loadingShift, setLoadingShift] = useState(false);

  // Batches & Freshness states
  const [batchesData, setBatchesData] = useState({ batches: [], summary: {} });
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  // Special Prices & AI Deal Advisor states
  const [customUnitPrice, setCustomUnitPrice] = useState(null);
  const [dealAdvisorData, setDealAdvisorData] = useState(null);
  const [dealAdvisorLoading, setDealAdvisorLoading] = useState(false);
  const [dealAdvisorModalOpen, setDealAdvisorModalOpen] = useState(false);

  // ── AI SMART FACE RECOGNITION & VOICE GREETING STATES ──
  const [showFaceModal, setShowFaceModal] = useState(false);
  const [faceRecognizedCustomer, setFaceRecognizedCustomer] = useState(null);
  const [faceScanStatus, setFaceScanStatus] = useState('Yuz qidirilmoqda...');
  const [faceConfidence, setFaceConfidence] = useState(null);
  const [isFaceVoiceEnabled, setIsFaceVoiceEnabled] = useState(true);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isFaceModelLoaded, setIsFaceModelLoaded] = useState(false);
  const [faceLoadingStatus, setFaceLoadingStatus] = useState('AI Neyrotarmoq yuklanmoqda...');
  const [live128Vector, setLive128Vector] = useState('🧠 128-D Vektor: Yuz qidirilmoqda...');
  const [faceModalTab, setFaceModalTab] = useState('assign'); // 'assign' | 'create'
  const [faceCustSearchText, setFaceCustSearchText] = useState('');
  const [faceSelectedCust, setFaceSelectedCust] = useState(null);
  const [aiNewCustName, setAiNewCustName] = useState('');
  const [aiNewCustPhone, setAiNewCustPhone] = useState('');
  const [availableCameras, setAvailableCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [cameraFacingMode, setCameraFacingMode] = useState('user'); // 'user' (oldi) or 'environment' (orqa)
  const [faceAssignCustId, setFaceAssignCustId] = useState('');
  const [faceAssignSaving, setFaceAssignSaving] = useState(false);
  const [faceAssignSuccessMsg, setFaceAssignSuccessMsg] = useState('');
  
  // ⚙️ AI Voice & Camera Settings
  const [showAiSettings, setShowAiSettings] = useState(false);
  const [aiVoiceVolume, setAiVoiceVolume] = useState(() => parseFloat(localStorage.getItem('mf_ai_vol') || '1.0'));
  const [aiVoiceRate, setAiVoiceRate] = useState(() => parseFloat(localStorage.getItem('mf_ai_rate') || '0.95'));
  const [aiVoicePitch, setAiVoicePitch] = useState(() => parseFloat(localStorage.getItem('mf_ai_pitch') || '1.05'));
  const [aiVoiceCooldown, setAiVoiceCooldown] = useState(() => parseInt(localStorage.getItem('mf_ai_cooldown') || '20', 10));
  const [aiGazeDuration, setAiGazeDuration] = useState(() => parseInt(localStorage.getItem('mf_ai_gaze') || '2', 10));
  const [aiVoiceVoiceURI, setAiVoiceVoiceURI] = useState(() => localStorage.getItem('mf_ai_voice_uri') || '');
  const [aiMirrorVideo, setAiMirrorVideo] = useState(() => localStorage.getItem('mf_ai_mirror') !== 'false');
  const [availableSynthVoices, setAvailableSynthVoices] = useState([]);

  const faceVideoRef = useRef(null);
  const faceCanvasRef = useRef(null);
  const faceStreamRef = useRef(null);
  const faceScanIntervalRef = useRef(null);
  const faceMatcherRef = useRef(null);
  const customerFaceDescriptorsRef = useRef([]);
  const lastExtractedDescriptorRef = useRef(null);
  const lastGreetedCustIdRef = useRef(null);
  const lastGreetingTimeRef = useRef(0);
  const presenceDwellCountRef = useRef(0); // Counts consecutive frames face was seen (2-3s gaze filter)

  const fetchShiftStatus = async () => {
    try {
      const res = await fetch('/pos/api/shift/current/');
      const data = await res.json();
      setShiftData(data);
    } catch (e) {
      console.error("Error fetching shift status:", e);
    }
  };

  const fetchBatchesData = async () => {
    try {
      const res = await fetch('/pos/api/reports/yield-decay/');
      const data = await res.json();
      setBatchesData(data);
    } catch (e) {
      console.error("Error loading batches:", e);
    }
  };

  // Create customer form
  const [showAddCustomer, setShowAddCustomer] = useState(false);
  const [custFirstName, setCustFirstName] = useState('');
  const [custLastName, setCustLastName] = useState('');
  const [custPhone, setCustPhone] = useState('');
  const [custCustomId, setCustCustomId] = useState('');
  const [custError, setCustError] = useState('');
  const [custDebtLimit, setCustDebtLimit] = useState('1000000');
  const [newCustSpecialPrices, setNewCustSpecialPrices] = useState({}); // { [productId]: price }

  // POS Customer Special Prices Modal
  const [posSpCustomer, setPosSpCustomer] = useState(null);
  const [posSpModalOpen, setPosSpModalOpen] = useState(false);
  const [posSpList, setPosSpList] = useState([]);
  const [posSpSelectedProduct, setPosSpSelectedProduct] = useState('');
  const [posSpPriceInput, setPosSpPriceInput] = useState('');
  const [posSpNotesInput, setPosSpNotesInput] = useState('');

  // POS Customer Debt History Modal
  const [posDebtHistCustomer, setPosDebtHistCustomer] = useState(null);
  const [posDebtHistModalOpen, setPosDebtHistModalOpen] = useState(false);
  const [posDebtHistData, setPosDebtHistData] = useState(null);
  const [posDebtHistLoading, setPosDebtHistLoading] = useState(false);

  const openPosCustomerDebtHistory = async (cust) => {
    setPosDebtHistCustomer(cust);
    setPosDebtHistModalOpen(true);
    setPosDebtHistLoading(true);
    setPosDebtHistData(null);
    try {
      const res = await fetch(`/pos/api/customers/${cust.id}/debt-history/`);
      const data = await res.json();
      if (data.status === 'success') {
        setPosDebtHistData(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setPosDebtHistLoading(false);
    }
  };

  // Fetch Products, Customers, Shift & Batches on Mount
  useEffect(() => {
    fetch('/pos/api/products/')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setProducts(data);
        else setProducts([]);
      })
      .catch(err => {
        console.error("Error loading products:", err);
        setProducts([]);
      });

    fetch('/pos/api/customers/')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setCachedCustomers(data);
        else setCachedCustomers([]);
      })
      .catch(err => {
        console.error("Error loading cached customers:", err);
        setCachedCustomers([]);
      });

    fetchShiftStatus();
    fetchBatchesData();
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

  // ── AI FACE CAMERA & BIOMETRIC NEURAL ENGINE ──
  const loadFaceApiModels = async () => {
    try {
      if (faceapi.nets.tinyFaceDetector.isLoaded && faceapi.nets.faceLandmark68Net.isLoaded && faceapi.nets.faceRecognitionNet.isLoaded) {
        setIsFaceModelLoaded(true);
        setFaceLoadingStatus("✅ AI Neyrotarmoq tayyor");
        await loadCustomerDescriptors();
        return;
      }

      setFaceLoadingStatus("AI Neyromodellar yuklanmoqda...");
      const MODEL_URL = '/models';
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
        faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
      ]);
      setIsFaceModelLoaded(true);
      setFaceLoadingStatus("✅ AI Neyrotarmoq tayyor");
      console.log("FaceAPI Neural Models loaded from /models");
      await loadCustomerDescriptors();
    } catch (err) {
      console.warn("Could not load from /models, trying /static/models fallback:", err);
      try {
        const FALLBACK_URL = '/static/models';
        await Promise.all([
          faceapi.nets.tinyFaceDetector.loadFromUri(FALLBACK_URL),
          faceapi.nets.faceLandmark68Net.loadFromUri(FALLBACK_URL),
          faceapi.nets.faceRecognitionNet.loadFromUri(FALLBACK_URL)
        ]);
        setIsFaceModelLoaded(true);
        setFaceLoadingStatus("✅ AI Neyrotarmoq tayyor");
        console.log("FaceAPI Neural Models loaded from /static/models");
        await loadCustomerDescriptors();
      } catch (fallbackErr) {
        console.error("Failed to load FaceAPI models:", fallbackErr);
        setFaceLoadingStatus("⚠️ Neyromodel yuklanmadi");
      }
    }
  };

  const loadCustomerDescriptors = async () => {
    try {
      const res = await fetch('/pos/api/ai/customers-face-descriptors/');
      const data = await res.json();
      if (data.status === 'success' && Array.isArray(data.customers)) {
        customerFaceDescriptorsRef.current = data.customers;
        const labeledList = [];
        data.customers.forEach(c => {
          if (c.face_descriptor && Array.isArray(c.face_descriptor) && c.face_descriptor.length >= 64) {
            labeledList.push(
              new faceapi.LabeledFaceDescriptors(String(c.id), [new Float32Array(c.face_descriptor)])
            );
          }
        });
        if (labeledList.length > 0) {
          // Standard Euclidean distance threshold 0.60 allows natural poses & angles
          faceMatcherRef.current = new faceapi.FaceMatcher(labeledList, 0.60);
          console.log(`FaceMatcher loaded with ${labeledList.length} customer biometric profiles`);
        } else {
          faceMatcherRef.current = null;
        }
      }
    } catch (e) {
      console.error("Error loading customer face descriptors:", e);
    }
  };

  const loadAvailableCameras = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter(d => d.kind === 'videoinput');
      setAvailableCameras(videoInputs);
    } catch (e) {
      console.warn("Could not enumerate camera devices:", e);
    }
  };

  const startFaceCamera = async (forcedFacingMode = null, forcedDeviceId = null) => {
    try {
      // Ensure neural models and descriptors are loaded
      loadFaceApiModels();

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Kameraga ulanish imkoni bo'lmadi (Brauzer kamera ruxsatini yoqing)");
        return;
      }

      // Stop existing stream if switching
      if (faceStreamRef.current) {
        faceStreamRef.current.getTracks().forEach(t => t.stop());
        faceStreamRef.current = null;
      }

      const activeFacing = forcedFacingMode || cameraFacingMode;
      const activeDeviceId = forcedDeviceId !== null ? forcedDeviceId : selectedCameraId;

      let videoConstraints = { width: { ideal: 1280, max: 1920 }, height: { ideal: 720, max: 1080 } };

      if (activeDeviceId) {
        videoConstraints.deviceId = { exact: activeDeviceId };
      } else if (activeFacing) {
        videoConstraints.facingMode = activeFacing;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints,
        audio: false
      });

      faceStreamRef.current = stream;
      if (faceVideoRef.current) {
        faceVideoRef.current.srcObject = stream;
      }
      setIsCameraActive(true);
      setFaceScanStatus("👀 AI Kamera faol — Yuz skanerlanmoqda...");

      // Load camera devices list once permission granted
      loadAvailableCameras();

      if (!faceScanIntervalRef.current) {
        faceScanIntervalRef.current = setInterval(() => {
          scanFaceSnapshot(true);
        }, 1200); // Scans every 1.2s for rapid neural face tracking
      }
    } catch (err) {
      console.error("Camera error:", err);
      // Fallback try simple video
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        faceStreamRef.current = stream;
        if (faceVideoRef.current) faceVideoRef.current.srcObject = stream;
        setIsCameraActive(true);
        setFaceScanStatus("👀 Kamera faol");
        loadAvailableCameras();
      } catch (fallbackErr) {
        setFaceScanStatus("Kameraga ulanib bo'lmadi");
        setIsCameraActive(false);
      }
    }
  };

  const stopFaceCamera = () => {
    if (faceScanIntervalRef.current) {
      clearInterval(faceScanIntervalRef.current);
      faceScanIntervalRef.current = null;
    }
    if (faceStreamRef.current) {
      faceStreamRef.current.getTracks().forEach(t => t.stop());
      faceStreamRef.current = null;
    }
    if (faceVideoRef.current) {
      faceVideoRef.current.srcObject = null;
    }
    if (faceCanvasRef.current) {
      const ctx = faceCanvasRef.current.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, faceCanvasRef.current.width, faceCanvasRef.current.height);
    }
    presenceDwellCountRef.current = 0;
    setIsCameraActive(false);
    setFaceScanStatus("Kamera o'chirilgan");
  };

  const toggleFaceCamera = () => {
    if (isCameraActive) {
      stopFaceCamera();
    } else {
      startFaceCamera();
    }
  };

  const switchCameraFacingMode = () => {
    const nextMode = cameraFacingMode === 'user' ? 'environment' : 'user';
    setCameraFacingMode(nextMode);
    setSelectedCameraId('');
    startFaceCamera(nextMode, '');
  };

  const selectSpecificCamera = (deviceId) => {
    setSelectedCameraId(deviceId);
    startFaceCamera(null, deviceId);
  };

  const scanFaceSnapshot = async (isAuto = false) => {
    const video = faceVideoRef.current;
    const canvas = faceCanvasRef.current;
    if (!video || !video.videoWidth || !canvas) return;

    try {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Check if neural detector is ready
      if (!faceapi.nets.tinyFaceDetector.isLoaded) {
        if (!isAuto) setFaceScanStatus("AI Neyromodel yuklanmoqda...");
        return;
      }

      // 1. Detect single face with 68 landmarks and 128-d descriptor
      const detection = await faceapi
        .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.45 }))
        .withFaceLandmarks()
        .withFaceDescriptor();

      if (!detection) {
        presenceDwellCountRef.current = 0;
        if (!isAuto) {
          setFaceScanStatus("👀 Kamera oldida yuz topilmadi");
          setFaceConfidence(null);
        }
        return;
      }

      const { detection: detBox, landmarks, descriptor } = detection;
      const box = detBox.box;
      if (descriptor) {
        lastExtractedDescriptorRef.current = Array.from(descriptor);
        const preview = Array.from(descriptor.slice(0, 6)).map(v => v.toFixed(3)).join(', ');
        setLive128Vector(`🧠 128-D: [${preview}, ...] (68 Nuqta)`);
      }

      // 1. Draw 68 Facial Landmarks Mesh Points
      if (landmarks && landmarks.positions) {
        ctx.fillStyle = '#38BDF8';
        landmarks.positions.forEach(p => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 2.2, 0, 2 * Math.PI);
          ctx.fill();
        });
      }

      // 2. Draw Cyber Neural Bounding Box on Canvas
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 3;
      ctx.strokeRect(box.x, box.y, box.width, box.height);

      // Draw Target Corners
      const cl = Math.min(22, box.width / 4);
      ctx.strokeStyle = '#38BDF8';
      ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(box.x, box.y + cl); ctx.lineTo(box.x, box.y); ctx.lineTo(box.x + cl, box.y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(box.right - cl, box.y); ctx.lineTo(box.right, box.y); ctx.lineTo(box.right, box.y + cl); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(box.x, box.bottom - cl); ctx.lineTo(box.x, box.bottom); ctx.lineTo(box.x + cl, box.bottom); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(box.right - cl, box.bottom); ctx.lineTo(box.right, box.bottom); ctx.lineTo(box.right, box.bottom - cl); ctx.stroke();

      const now = Date.now();
      let bestMatchedCustomer = null;
      let matchConfidence = 0;

      // 3. Biometric matching against loaded customer embeddings
      if (faceMatcherRef.current && descriptor) {
        const match = faceMatcherRef.current.findBestMatch(descriptor);
        if (match && match.label !== 'unknown') {
          const custId = parseInt(match.label, 10);
          bestMatchedCustomer = customerFaceDescriptorsRef.current.find(c => c.id === custId);
          matchConfidence = Math.max(50, Math.min(99, Math.round((1 - match.distance / 0.6) * 100)));
        }
      }

      if (bestMatchedCustomer) {
        const c = bestMatchedCustomer;
        setFaceRecognizedCustomer(c);
        setFaceConfidence(matchConfidence);
        presenceDwellCountRef.current += 1;

        // Draw Identified Name Tag on HUD Canvas
        const tagText = `✨ ${c.name} (${matchConfidence}%)`;
        ctx.font = 'bold 13px sans-serif';
        const tagW = ctx.measureText(tagText).width + 16;
        ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
        ctx.fillRect(box.x, Math.max(0, box.y - 28), tagW, 26);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText(tagText, box.x + 8, Math.max(16, box.y - 10));

        if (presenceDwellCountRef.current < aiGazeDuration && isAuto) {
          setFaceScanStatus(`🎯 ${c.name} aniqlandi...`);
          return;
        }

        setFaceScanStatus(`✨ Tanildi: ${c.name} (${matchConfidence}% aniqlik)`);

        // Cooldown per recognized person so it doesn't shout repeatedly
        const cooldownMs = (aiVoiceCooldown || 20) * 1000;
        if (lastGreetedCustIdRef.current !== c.id || (now - lastGreetingTimeRef.current) > cooldownMs) {
          lastGreetedCustIdRef.current = c.id;
          lastGreetingTimeRef.current = now;

          let greeting = `Assalomu alaykum, ${c.first_name}! Baxmal Meat sarxil go'shtlar do'koniga xush kelibsiz!`;
          if (c.bonus_points >= 2000) {
            greeting = `Assalomu alaykum, hurmatli VIP mijozimiz ${c.first_name}! Baxmal Meat sarxil go'shtlar do'koniga xush kelibsiz! Sizda ${c.bonus_points} ta bonus mavjud.`;
          } else if (c.debt_amount > 0) {
            greeting = `Assalomu alaykum, ${c.first_name}! Do'konimizga xush kelibsiz! Bugun qanday sarxil go'sht tortib beraylik?`;
          }
          playAiVoiceGreeting(greeting);
        }
      } else {
        // Unknown visitor detected in front of camera
        presenceDwellCountRef.current += 1;

        ctx.fillStyle = 'rgba(14, 165, 233, 0.85)';
        ctx.fillRect(box.x, Math.max(0, box.y - 26), 130, 24);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText("👋 Yangi Xaridor", box.x + 6, Math.max(15, box.y - 9));

        if (presenceDwellCountRef.current < aiGazeDuration && isAuto) {
          setFaceScanStatus("🎯 Xaridor qaramoqda... (Kutilmoqda)");
          return;
        }

        if (!isAuto) {
          setFaceScanStatus("👋 Xaridor ko'rindi (Face ID ro'yxatida yo'q)");
          setFaceConfidence(null);
        } else {
          setFaceScanStatus("👋 Xaridor qaramoqda");
        }

        // Greet any visitor who looks at the camera (cooldown)
        const cooldownMs = (aiVoiceCooldown || 25) * 1000;
        if ((now - lastGreetingTimeRef.current) > cooldownMs) {
          lastGreetedCustIdRef.current = 'visitor_' + Math.floor(now / cooldownMs);
          lastGreetingTimeRef.current = now;
          const visitorGreetings = [
            "Assalomu alaykum! Baxmal Meat sarxil go'shtlar do'koniga xush kelibsiz! Marhamat, yangi so'yilgan sarxil go'shtlarimizdan tanlang!",
            "Xush kelibsiz! Bugun do'konimizda yangi mol va qo'y go'shtlari keltirildi. Qaysi biridan tortib beraylik?",
            "Assalomu alaykum, aziz xaridor! Sog'lom va halol go'shtlarimiz siz uchun tayyor, marhamat!"
          ];
          const randomGreeting = visitorGreetings[Math.floor(Math.random() * visitorGreetings.length)];
          playAiVoiceGreeting(randomGreeting);
          setFaceScanStatus("👋 Xaridorga salom berildi!");
        }
      }
    } catch (e) {
      console.error("Scan face error:", e);
    }
  };

  const handleSaveFaceToCustomer = async () => {
    if (!faceAssignCustId) {
      alert("Iltimos, avval ro'yxatdan mijozni tanlang!");
      return;
    }
    const video = faceVideoRef.current;
    const canvas = faceCanvasRef.current;
    if (!video || !video.videoWidth || !canvas) {
      alert("Kamera tasviri topilmadi. Kamerani yoqing!");
      return;
    }

    try {
      setFaceAssignSaving(true);
      setFaceScanStatus("🔍 Yuz biometriyasi tahlil qilinmoqda...");

      // 1. Detect face and compute 128-d neural descriptor
      let descriptorArray = null;
      if (faceapi.nets.tinyFaceDetector.isLoaded) {
        const detection = await faceapi
          .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.35 }))
          .withFaceLandmarks()
          .withFaceDescriptor();

        if (detection && detection.descriptor) {
          descriptorArray = Array.from(detection.descriptor);
        }
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imgBase64 = canvas.toDataURL('image/jpeg', 0.85);

      const res = await fetch('/pos/api/ai/save-customer-face/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          customer_id: faceAssignCustId,
          image: imgBase64,
          descriptor: descriptorArray
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setFaceAssignSuccessMsg("✅ Face ID muvaffaqiyatli saqlandi! Endi kamera bu mijozni har qanday holatda darhol taniydi.");
        
        // Reload customer descriptors into FaceMatcher
        await loadCustomerDescriptors();

        // Refresh customer list in POS
        fetch('/pos/api/customers/')
          .then(r => r.json())
          .then(d => { if (Array.isArray(d)) setCachedCustomers(d); });
        
        // Immediate scan to verify recognition
        setTimeout(() => {
          scanFaceSnapshot(false);
        }, 500);
      } else {
        alert(`❌ Xatolik: ${data.message || "Saqlab bo'lmadi"}`);
      }
    } catch (err) {
      console.error("Save face error:", err);
      alert("Saqlashda xatolik yuz berdi: " + err.message);
    } finally {
      setFaceAssignSaving(false);
    }
  };

  const handleCreateNewCustomerWithFace = async () => {
    if (!aiNewCustName.trim() || !aiNewCustPhone.trim()) {
      alert("Iltimos, Ism va Telefon raqamini to'liq kiriting!");
      return;
    }
    const video = faceVideoRef.current;
    if (!video || !video.videoWidth) {
      alert("Kamera tasviri topilmadi!");
      return;
    }

    // 1. Instant descriptor extraction directly from current video frame
    let descriptorToSave = lastExtractedDescriptorRef.current;
    try {
      if (faceapi.nets.tinyFaceDetector.isLoaded) {
        const instantDet = await faceapi
          .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.3 }))
          .withFaceLandmarks()
          .withFaceDescriptor();
        if (instantDet && instantDet.descriptor) {
          descriptorToSave = Array.from(instantDet.descriptor);
        }
      }
    } catch (err) {
      console.warn("Instant descriptor extraction error:", err);
    }

    if (!descriptorToSave || descriptorToSave.length < 64) {
      alert("⚠️ Yuz aniq topilmadi! Iltimos, yuzingizni kameraga to'g'ri qaratib qayta urinib ko'ring.");
      return;
    }

    try {
      setFaceAssignSaving(true);
      const snapCanvas = document.createElement('canvas');
      snapCanvas.width = video.videoWidth;
      snapCanvas.height = video.videoHeight;
      const ctx = snapCanvas.getContext('2d');
      ctx.drawImage(video, 0, 0, snapCanvas.width, snapCanvas.height);
      const imgBase64 = snapCanvas.toDataURL('image/jpeg', 0.85);

      const res = await fetch('/pos/api/ai/create-customer-with-face/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          name: aiNewCustName.trim(),
          phone: aiNewCustPhone.trim(),
          debt_limit: '1000000',
          image: imgBase64,
          descriptor: descriptorToSave
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setFaceAssignSuccessMsg("✅ " + data.message);
        setAiNewCustName('');
        setAiNewCustPhone('');
        await loadCustomerDescriptors();
        fetch('/pos/api/customers/')
          .then(r => r.json())
          .then(d => { if (Array.isArray(d)) setCachedCustomers(d); });
        setTimeout(() => {
          scanFaceSnapshot(false);
        }, 500);
      } else {
        alert("❌ Xatolik: " + data.message);
      }
    } catch (e) {
      alert("Xatolik yuz berdi: " + e.message);
    } finally {
      setFaceAssignSaving(false);
    }
  };

  // Load synth voices & FaceAI models on mount
  useEffect(() => {
    loadFaceApiModels();
    loadCustomerDescriptors();

    if ('speechSynthesis' in window) {
      const updateVoices = () => {
        const v = window.speechSynthesis.getVoices();
        if (v && v.length) setAvailableSynthVoices(v);
      };
      updateVoices();
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  const saveAiSettingsToStorage = (updates = {}) => {
    const vol = updates.vol !== undefined ? updates.vol : aiVoiceVolume;
    const rate = updates.rate !== undefined ? updates.rate : aiVoiceRate;
    const pitch = updates.pitch !== undefined ? updates.pitch : aiVoicePitch;
    const cooldown = updates.cooldown !== undefined ? updates.cooldown : aiVoiceCooldown;
    const gaze = updates.gaze !== undefined ? updates.gaze : aiGazeDuration;
    const voiceUri = updates.voiceUri !== undefined ? updates.voiceUri : aiVoiceVoiceURI;
    const mirror = updates.mirror !== undefined ? updates.mirror : aiMirrorVideo;

    localStorage.setItem('mf_ai_vol', vol.toString());
    localStorage.setItem('mf_ai_rate', rate.toString());
    localStorage.setItem('mf_ai_pitch', pitch.toString());
    localStorage.setItem('mf_ai_cooldown', cooldown.toString());
    localStorage.setItem('mf_ai_gaze', gaze.toString());
    localStorage.setItem('mf_ai_voice_uri', voiceUri);
    localStorage.setItem('mf_ai_mirror', mirror.toString());
  };

  const resetAiSettingsToDefault = () => {
    setAiVoiceVolume(1.0);
    setAiVoiceRate(0.95);
    setAiVoicePitch(1.05);
    setAiVoiceCooldown(20);
    setAiGazeDuration(2);
    setAiVoiceVoiceURI('');
    setAiMirrorVideo(true);
    saveAiSettingsToStorage({ vol: 1.0, rate: 0.95, pitch: 1.05, cooldown: 20, gaze: 2, voiceUri: '', mirror: true });
    alert("✅ Sozlamalar standart holatga qaytarildi!");
  };

  const testAiVoice = () => {
    playAiVoiceGreeting("Assalomu alaykum! Baxmal Meat sarxil go'shtlar do'koniga xush kelibsiz! Ovoz sozlamalari muvaffaqiyatli sinovdan o'tdi.");
  };

  const playAiVoiceGreeting = (text) => {
    if (!isFaceVoiceEnabled) return;
    try {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        const audioCtx = new AudioCtxClass();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1320, audioCtx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.12 * aiVoiceVolume, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.3);
      }
    } catch (e) {}

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'uz-UZ';
      utterance.volume = Math.max(0.1, Math.min(1.0, aiVoiceVolume));
      utterance.rate = Math.max(0.6, Math.min(1.5, aiVoiceRate));
      utterance.pitch = Math.max(0.6, Math.min(1.5, aiVoicePitch));

      const voices = window.speechSynthesis.getVoices();
      let matchedVoice = null;
      if (aiVoiceVoiceURI) {
        matchedVoice = voices.find(v => v.voiceURI === aiVoiceVoiceURI || v.name === aiVoiceVoiceURI);
      }
      if (!matchedVoice) {
        matchedVoice = voices.find(v => v.lang.startsWith('uz') || v.lang.startsWith('tr') || v.lang.startsWith('ru'));
      }
      if (matchedVoice) utterance.voice = matchedVoice;
      window.speechSynthesis.speak(utterance);
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
        .then(data => {
          if (Array.isArray(data)) setCustomers(data);
          else setCustomers([]);
        })
        .catch(err => {
          console.error("Customer search error:", err);
          setCustomers([]);
        });
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
      const standardPrice = parseFloat(selectedProduct.price_per_kg) || 0;
      const unitPrice = customUnitPrice !== null ? customUnitPrice : standardPrice;
      const exact = Math.round(weight * unitPrice);
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
  }, [step, selectedProduct, weight, customUnitPrice]);

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
    setCustomUnitPrice(null);
    setStep(2);
  };

  const handleConfirmCustomer = (cust) => {
    setSelectedCustomer(cust);
    if (cust && selectedProduct && Array.isArray(cust.special_prices)) {
      const sp = cust.special_prices.find(p => p.product_id === selectedProduct.id);
      if (sp && sp.special_price > 0) {
        setCustomUnitPrice(sp.special_price);
      } else {
        setCustomUnitPrice(null);
      }
    } else {
      setCustomUnitPrice(null);
    }
    setStep(3);
  };

  const handleConsultDealAdvisor = async () => {
    if (!selectedProduct || weight <= 0) return;
    const standardPrice = parseFloat(selectedProduct.price_per_kg) || 0;
    const unitPrice = customUnitPrice !== null ? customUnitPrice : standardPrice;

    setDealAdvisorLoading(true);
    setDealAdvisorModalOpen(true);
    try {
      const res = await fetch('/pos/api/ai/deal-advisor/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          items: [
            {
              product_id: selectedProduct.id,
              product_name: selectedProduct.name,
              weight: weight,
              offered_price: unitPrice
            }
          ]
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setDealAdvisorData(data);
      } else {
        alert(data.message || "Tahlilda xatolik!");
        setDealAdvisorModalOpen(false);
      }
    } catch (err) {
      alert("Tarmoq xatosi: " + err.message);
      setDealAdvisorModalOpen(false);
    } finally {
      setDealAdvisorLoading(false);
    }
  };

  const handleEditUnitPricePrompt = () => {
    const standardPrice = selectedProduct ? parseFloat(selectedProduct.price_per_kg) : 0;
    const currentPrice = customUnitPrice !== null ? customUnitPrice : standardPrice;
    const input = prompt(`1 kg "${selectedProduct?.name}" uchun kelishilgan narxni kiriting (so'm/kg):`, currentPrice);
    if (input !== null) {
      const parsed = parseFloat(input.replace(/\s+/g, ''));
      if (!isNaN(parsed) && parsed > 0) {
        setCustomUnitPrice(parsed);
      } else {
        alert("Noto'g'ri narx kiritildi!");
      }
    }
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

  const handleSaveCustomer = async () => {
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

    try {
      const res = await fetch('/pos/api/customers/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
      });
      const data = await res.json();
      if (data.error) {
        setCustError(data.error);
      } else {
        // Save initial special prices if provided
        const spEntries = Object.entries(newCustSpecialPrices);
        for (let [pId, pVal] of spEntries) {
          if (pVal && parseFloat(pVal) > 0) {
            try {
              await fetch(`/pos/api/customers/${data.id}/special-prices/`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                  product_id: pId,
                  special_price: parseFloat(pVal),
                  notes: "Choyxona / Ro'yxatdan o'tishda biriktirildi"
                })
              });
            } catch (spErr) {
              console.error("Error saving special price:", spErr);
            }
          }
        }

        // Fetch fresh special prices for this new customer
        let freshSpList = [];
        try {
          const freshRes = await fetch(`/pos/api/customers/${data.id}/special-prices/`);
          const freshData = await freshRes.json();
          freshSpList = freshData.special_prices || [];
        } catch (e) {}

        const createdCust = {
          id: data.id,
          name: data.name || `${data.first_name || ''} ${data.last_name || ''}`.trim(),
          custom_id: data.custom_id,
          phone: data.phone,
          bonus_points: data.bonus_points || 0,
          debt_amount: data.debt_amount || 0,
          debt_limit: data.debt_limit || 1000000,
          credit_score: data.credit_score || 'B (Yangi)',
          special_prices: freshSpList
        };

        setSelectedCustomer(createdCust);
        setShowAddCustomer(false);

        // Apply custom unit price if selectedProduct matches
        if (selectedProduct) {
          const sp = freshSpList.find(p => p.product_id === selectedProduct.id);
          if (sp && sp.special_price > 0) {
            setCustomUnitPrice(sp.special_price);
          } else {
            setCustomUnitPrice(null);
          }
        }

        // reset form
        setCustFirstName('');
        setCustLastName('');
        setCustPhone('');
        setCustCustomId('');
        setCustDebtLimit('1000000');
        setNewCustSpecialPrices({});
        if (fileInput) fileInput.value = '';
        reloadProductsAndCustomers();
        setStep(3);
      }
    } catch (err) {
      setCustError("Mijozni saqlashda xatolik: " + err.message);
    }
  };

  // POS Customer Special Prices Modal Handlers
  const openPosCustomerSpecialPrices = (customer) => {
    setPosSpCustomer(customer);
    setPosSpModalOpen(true);
    setPosSpSelectedProduct('');
    setPosSpPriceInput('');
    setPosSpNotesInput('');
    loadPosCustomerSpecialPrices(customer.id);
  };

  const loadPosCustomerSpecialPrices = async (customerId) => {
    try {
      const res = await fetch(`/pos/api/customers/${customerId}/special-prices/`);
      const data = await res.json();
      if (data.special_prices) {
        setPosSpList(data.special_prices);
      }
    } catch (err) {
      console.error("Error loading special prices:", err);
    }
  };

  const handleSavePosSpecialPrice = async () => {
    if (!posSpCustomer || !posSpSelectedProduct || !posSpPriceInput) {
      alert("Iltimos, mahsulot va narxni to'ldiring!");
      return;
    }
    try {
      const res = await fetch(`/pos/api/customers/${posSpCustomer.id}/special-prices/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          product_id: posSpSelectedProduct,
          special_price: parseFloat(posSpPriceInput),
          notes: posSpNotesInput || 'Choyxona / Maxsus narx'
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setPosSpPriceInput('');
        setPosSpNotesInput('');
        loadPosCustomerSpecialPrices(posSpCustomer.id);
        reloadProductsAndCustomers();
      } else {
        alert("Xatolik: " + data.message);
      }
    } catch (err) {
      alert("Aloqa xatosi: " + err.message);
    }
  };

  const handleDeletePosSpecialPrice = async (priceId) => {
    if (!posSpCustomer || !priceId) return;
    if (!window.confirm("Ushbu maxsus narxni o'chirasizmi?")) return;
    try {
      const res = await fetch(`/pos/api/customers/${posSpCustomer.id}/special-prices/${priceId}/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ price_id: priceId })
      });
      const data = await res.json();
      if (data.status === 'success') {
        loadPosCustomerSpecialPrices(posSpCustomer.id);
        reloadProductsAndCustomers();
      } else {
        alert("Xatolik: " + data.message);
      }
    } catch (err) {
      alert("Aloqa xatosi: " + err.message);
    }
  };

  // Reload products and customers
  const reloadProductsAndCustomers = () => {
    fetch('/pos/api/products/')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data)) setProducts(data); })
      .catch(() => {});
    fetch('/pos/api/customers/')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data)) setCachedCustomers(data); })
      .catch(() => {});
    fetchShiftStatus();
  };

  // Open Shift Submit
  const handleOpenShiftSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoadingShift(true);
    try {
      const res = await fetch('/pos/api/shift/open/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({
          opening_cash: parseFloat(shiftOpeningCash) || 0,
          notes: shiftNotes
        })
      });
      const data = await res.json();
      if (res.ok) {
        setShiftModalOpen(false);
        setShiftNotes('');
        fetchShiftStatus();
        alert('✅ Yangi kassa smenasi muvaffaqiyatli ochildi!');
      } else {
        alert(data.error || 'Smena ochishda xatolik!');
      }
    } catch (err) {
      alert('Tarmoq xatosi: ' + err.message);
    } finally {
      setLoadingShift(false);
    }
  };

  // Close Shift Submit
  const handleCloseShiftSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!window.confirm("Haqiqatan ham kassa smenasini yopib, Z-Hisobot chiqarmoqchimisiz?")) return;
    setLoadingShift(true);
    try {
      const res = await fetch('/pos/api/shift/close/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({
          closed_cash_actual: parseFloat(shiftActualCash) || 0,
          notes: shiftNotes
        })
      });
      const data = await res.json();
      if (res.ok && (data.z_report || data.status === 'success')) {
        if (data.z_report) {
          setZReportData(data.z_report);
        } else {
          alert('✅ Smena muvaffaqiyatli yopildi!');
        }
        setShiftModalOpen(false);
        setShiftNotes('');
        fetchShiftStatus();
      } else {
        alert(data.message || data.error || 'Smenani yopishda xatolik!');
      }
    } catch (err) {
      alert('Tarmoq xatosi: ' + err.message);
    } finally {
      setLoadingShift(false);
    }
  };

  // Handle payment method switch
  const handlePaymentMethodChange = (method) => {
    setPaymentMethod(method);
    if (method === 'aralash') {
      const half = Math.round(selectedAmount / 2 / 1000) * 1000;
      setSplitNaqd(half);
      setSplitKarta(selectedAmount - half);
      setSplitQr(0);
      setSplitNasiya(0);
    }
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

    const standardPrice = parseFloat(selectedProduct.price_per_kg) || 0;
    const effectiveUnitPrice = customUnitPrice !== null ? customUnitPrice : standardPrice;
    const totalAmount = weight * effectiveUnitPrice;
    let finalPaid = selectedAmount;
    let discountAmount = totalAmount - selectedAmount;
    if (discountAmount < 0) discountAmount = 0;

    let bonusUsed = 0;
    let debtAdded = 0;
    let paidNaqd = 0;
    let paidKarta = 0;
    let paidQr = 0;

    if (paymentMethod === 'aralash') {
      paidNaqd = parseFloat(splitNaqd) || 0;
      paidKarta = parseFloat(splitKarta) || 0;
      paidQr = parseFloat(splitQr) || 0;
      const splitNasiyaNum = parseFloat(splitNasiya) || 0;

      finalPaid = paidNaqd + paidKarta + paidQr;
      debtAdded = splitNasiyaNum;

      const sumSplit = finalPaid + debtAdded;
      if (Math.abs(sumSplit - selectedAmount) > 100) {
        setLoadingSale(false);
        alert(`Aralash to'lov taqsimoti xato! Jami summa: ${selectedAmount.toLocaleString('fr-FR')} so'm, siz kiritganingiz: ${sumSplit.toLocaleString('fr-FR')} so'm.`);
        return;
      }

      if (debtAdded > 0 && !selectedCustomer) {
        setLoadingSale(false);
        alert("Nasiya qismi mavjud bo'lgani sababli, ro'yxatdan o'tgan mijozni tanlashingiz shart!");
        return;
      }
    } else if (paymentMethod === 'nasiya') {
      finalPaid = 0;
      debtAdded = selectedAmount;
    } else if (paymentMethod === 'naqd') {
      paidNaqd = selectedAmount;
    } else if (paymentMethod === 'karta') {
      paidKarta = selectedAmount;
    } else if (paymentMethod === 'qr') {
      paidQr = selectedAmount;
    }

    if (selectedCustomer && paymentMethod !== 'nasiya' && paymentMethod !== 'aralash' && discountAmount > 0) {
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
      paid_naqd: Math.round(paidNaqd),
      paid_karta: Math.round(paidKarta),
      paid_qr: Math.round(paidQr),
      items: [
        {
          product_id: selectedProduct.id,
          weight: weight,
          price_per_kg: effectiveUnitPrice
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
            status: "success",
            paid_naqd: paidNaqd,
            paid_karta: paidKarta,
            paid_qr: paidQr,
            debt_added: debtAdded
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
      .then(async res => {
        let data;
        try {
          data = await res.json();
        } catch (e) {
          data = null;
        }

        setLoadingSale(false);

        if (res.ok && (data?.status === 'success' || data?.sale_id)) {
          // Success
          setReceiptData({
            ...data,
            paid_naqd: paidNaqd,
            paid_karta: paidKarta,
            paid_qr: paidQr,
            debt_added: debtAdded
          });
          reloadProductsAndCustomers();
          setStep(4);
        } else if (data && (data.error || data.message || data.detail)) {
          // Explicit server error
          alert("Xatolik: " + (data.error || data.message || data.detail));
        } else {
          // Server unreachable -> offline fallback
          throw new Error("Serverga ulanib bo'lmadi");
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
              status: "success",
              paid_naqd: paidNaqd,
              paid_karta: paidKarta,
              paid_qr: paidQr,
              debt_added: debtAdded
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
    setSplitNaqd(0);
    setSplitKarta(0);
    setSplitQr(0);
    setSplitNasiya(0);
    setReceiptData(null);
    setSearchQuery('');
    setIsManualMode(false);
    setStep(1);
    // Restart polling
    handleScaleTabChange("1");
  };

  const handleVoidLastSale = async () => {
    try {
      // 1. Fetch last sale details
      const res = await fetch('/pos/api/sales/last/');
      const data = await res.json();
      
      if (data.status !== 'success' || !data.sale) {
        alert("Bekor qilish uchun oxirgi savdo topilmadi yoki hali savdo qilinmagan.");
        return;
      }
      
      const s = data.sale;
      const itemsSummary = (s.items || []).map(it => `${it.product_name}: ${it.weight} kg`).join(', ');
      const confirmText = `Oxirgi savdoni bekor qilasizmi?\n\n` +
        `🧾 Chek ID: #${s.id}\n` +
        `🥩 Mahsulotlar: ${itemsSummary || 'Go\'sht'}\n` +
        `👤 Xaridor: ${s.customer_name}\n` +
        `💰 Jami summa: ${parseFloat(s.total_amount || 0).toLocaleString('fr-FR')} so'm\n\n` +
        `⚠️ Ushbu amal go'sht zaxirasini (Stock) va mijoz hisobini avtomatik qaytaradi!`;

      if (!window.confirm(confirmText)) return;

      // 2. Call void API
      const voidRes = await fetch('/pos/api/sales/void/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ sale_id: s.id })
      });

      const voidData = await voidRes.json();
      if (voidData.status === 'success') {
        alert(`✅ ${voidData.message || 'Oxirgi savdo muvaffaqiyatli bekor qilindi va zaxira qaytarildi!'}`);
        // Reload products and customers stock
        fetch('/pos/api/products/')
          .then(r => r.json())
          .then(d => { if (Array.isArray(d)) setProducts(d); });
        fetch('/pos/api/customers/')
          .then(r => r.json())
          .then(d => { if (Array.isArray(d)) setCachedCustomers(d); });
        resetTerminal();
      } else {
        alert(`❌ Xatolik: ${voidData.message || 'Savdoni bekor qilib bo\'lmadi.'}`);
      }
    } catch (err) {
      console.error("Void sale error:", err);
      alert("Oxirgi savdoni bekor qilishda texnik xatolik yuz berdi: " + (err.message || err.toString()));
    }
  };

  return (
    <div className="pos-shell">
      {/* ════ LEFT PANEL ════ */}
      <div className="left-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '8px' }}>
          <div className="app-label" style={{ margin: 0 }}>MeatFlow POS</div>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <button
              onClick={() => { setShowFaceModal(true); startFaceCamera(); }}
              title="AI Smart Kamera & Face ID"
              style={{
                background: 'rgba(255,255,255,0.12)',
                color: '#81EFBB',
                border: '1px solid rgba(129,239,187,0.3)',
                borderRadius: '10px',
                padding: '6px 10px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                transition: 'all 0.2s'
              }}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#81EFBB', boxShadow: '0 0 6px #81EFBB', display: 'inline-block' }}></span>
              📷 Face ID
            </button>
            {recognition && (
              <button 
                onClick={toggleListening}
                className={`mic-btn ${isListening ? 'listening' : ''}`}
                title="Ovozli AI boshqaruv"
                style={{
                  width: '36px',
                  height: '36px',
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
        </div>

        {voiceStatus && (
          <div style={{ fontSize: '11px', color: '#D4A853', background: 'rgba(212,168,83,0.1)', border: '1px solid rgba(212,168,83,0.2)', padding: '8px 12px', borderRadius: '10px', marginBottom: '15px', textAlign: 'left', lineHeight: '1.4' }}>
            {voiceStatus}
          </div>
        )}

        {/* Connection status badge */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', padding: '10px 14px', background: 'rgba(255,255,255,0.06)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
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

        {/* Shift Management Status Button */}
        <div style={{ marginBottom: '14px' }}>
          {shiftData.is_open ? (
            <button
              onClick={() => {
                setShiftActualCash(shiftData.expected_cash?.toString() || '');
                setShiftModalOpen(true);
              }}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.25))',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: '#A7F3D0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 'bold',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981', display: 'inline-block', boxShadow: '0 0 8px #10B981' }}></span>
                <span>Smena #{shiftData.shift_id} (Ochiq)</span>
              </div>
              <span style={{ color: '#FDE68A', fontSize: '11px' }}>
                💰 {(shiftData.expected_cash || 0).toLocaleString('fr-FR')} so'm ⚙️
              </span>
            </button>
          ) : (
            <button
              onClick={() => {
                setShiftOpeningCash('0');
                setShiftModalOpen(true);
              }}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(185, 28, 28, 0.25))',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#FECACA',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 'bold',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#EF4444', display: 'inline-block' }}></span>
                <span>Smena yopiq</span>
              </div>
              <span style={{ background: '#EF4444', color: '#fff', padding: '3px 8px', borderRadius: '6px', fontSize: '11px' }}>
                Ochish 🔓
              </span>
            </button>
          )}
        </div>

        {/* Vitrina & Sovuqxona Nazorati Button */}
        <div style={{ marginBottom: '14px' }}>
          <button
            type="button"
            onClick={() => { fetchBatchesData(); setBatchModalOpen(true); }}
            style={{
              width: '100%',
              padding: '9px 12px',
              borderRadius: '12px',
              background: batchesData?.summary?.critical_count > 0 
                ? 'rgba(239, 68, 68, 0.2)' 
                : (batchesData?.summary?.warning_count > 0 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.08)'),
              border: '1px solid ' + (batchesData?.summary?.critical_count > 0 
                ? 'rgba(239, 68, 68, 0.5)' 
                : (batchesData?.summary?.warning_count > 0 ? 'rgba(245, 158, 11, 0.5)' : 'rgba(255, 255, 255, 0.15)')),
              color: batchesData?.summary?.critical_count > 0 
                ? '#FCA5A5' 
                : (batchesData?.summary?.warning_count > 0 ? '#FDE68A' : 'rgba(255, 255, 255, 0.9)'),
              fontWeight: '700',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              transition: 'all 0.15s'
            }}
          >
            <span>🥩 Vitrina & Sovuqxona</span>
            <span>
              {batchesData?.summary?.critical_count > 0 
                ? `🔴 ${batchesData.summary.critical_count} ta xavfli partiya` 
                : (batchesData?.summary?.warning_count > 0 
                ? `🟡 ${batchesData.summary.warning_count} ta ogohlantirish` 
                : '🟢 Barchasi yangi')}
            </span>
          </button>
        </div>

        <div className="scale-tabs" style={{ display: 'flex', gap: '6px', marginBottom: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
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
          style={{ cursor: 'pointer', marginBottom: '12px' }}
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

        <div className="prod-strip" style={{ marginBottom: '12px' }}>
          <div className="prod-strip-lbl">Mahsulot & Qoldiq</div>
          <div className={`prod-strip-val ${!selectedProduct ? 'none' : ''}`}>
            {selectedProduct ? (
              <div>
                <div>{selectedProduct.name}</div>
                <div style={{ fontSize: '12px', color: (selectedProduct.stock || 0) <= 5 ? '#FCA5A5' : '#86EFAC', fontWeight: 'bold', marginTop: '3px' }}>
                  📦 Omborda: {(selectedProduct.stock || 0).toFixed(2)} kg
                </div>
              </div>
            ) : 'Tanlanmagan'}
          </div>
        </div>

        {/* Quick Void / Cancel current sale buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
          {(weight > 0 || selectedProduct || step > 1) && (
            <button
              type="button"
              onClick={resetTerminal}
              style={{
                width: '100%',
                padding: '9px 12px',
                borderRadius: '12px',
                background: 'rgba(220, 53, 69, 0.2)',
                border: '1px solid rgba(220, 53, 69, 0.4)',
                color: '#FFB3BA',
                fontWeight: 'bold',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                transition: 'all 0.15s'
              }}
            >
              ❌ Bekor qilish (0 kg)
            </button>
          )}

          <button
            type="button"
            onClick={handleVoidLastSale}
            title="Oxirgi noto'g'ri kiritilgan savdoni bekor qilish va zaxirani qaytarish"
            style={{
              width: '100%',
              padding: '9px 12px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: 'rgba(255, 255, 255, 0.85)',
              fontWeight: '600',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.15s'
            }}
          >
            ⏪ Oxirgi savdoni bekor qilish
          </button>
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
            <div className="step-sub">Sotish uchun mahsulotni tanlang (Jonli ombor qoldig'i bilan)</div>
            <div className="prod-grid">
              {(Array.isArray(products) ? products : []).map(p => {
                if (!p) return null;
                const priceNum = parseFloat(p.price_per_kg) || 0;
                const stockNum = typeof p.stock === 'number' ? p.stock : 0;
                const isOut = stockNum <= 0;
                const isLow = stockNum > 0 && stockNum <= 10;

                return (
                  <button key={p.id || Math.random()} className="prod-btn" onClick={() => handleSelectProduct(p)}>
                    <div style={{ position: 'relative', width: '100%', height: '140px', borderRadius: '10px', overflow: 'hidden' }}>
                      <img 
                        src={p.image || 'https://cdn-icons-png.flaticon.com/512/1046/1046747.png'} 
                        alt={p.name || ''} 
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                      />
                      
                      {/* Live Stock Badge */}
                      <div style={{
                        position: 'absolute',
                        top: '8px',
                        right: '8px',
                        padding: '4px 8px',
                        borderRadius: '8px',
                        fontSize: '11px',
                        fontWeight: '800',
                        backdropFilter: 'blur(8px)',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                        background: isOut 
                          ? 'rgba(239, 68, 68, 0.92)' 
                          : isLow 
                          ? 'rgba(245, 158, 11, 0.92)' 
                          : 'rgba(16, 185, 129, 0.92)',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        zIndex: 2
                      }}>
                        <span>{isOut ? '🔴' : isLow ? '⚠️' : '🟢'}</span>
                        <span>{isOut ? '0 kg (Tugagan)' : `${stockNum.toFixed(1)} kg`}</span>
                      </div>

                      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.05) 55%, transparent 100%)' }}></div>
                      <div style={{ position: 'absolute', bottom: '10px', left: '12px', right: '12px', textAlign: 'left' }}>
                        <div className="prod-btn-name" style={{ color: '#fff' }}>{p.name || 'Mahsulot'}</div>
                        <div className="prod-btn-price" style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px', fontWeight: '600' }}>
                          {priceNum.toLocaleString('fr-FR')} so'm / kg
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
              {(!products || products.length === 0) && (
                <div className="prod-empty">Faol mahsulotlar topilmadi</div>
              )}
            </div>
          </div>
        )}

        {/* STEP 2: Customer Search / Selection */}
        {step === 2 && (
          <div className="fade-up">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div className="step-title" style={{ margin: 0 }}>Mijoz</div>
              <button
                type="button"
                onClick={() => { setShowFaceModal(true); startFaceCamera(); }}
                style={{
                  background: '#1B6B4A',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '7px 14px',
                  fontSize: '12px',
                  fontWeight: '800',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 4px 12px rgba(27,107,74,0.2)'
                }}
              >
                📷 AI Face ID Skaner
              </button>
            </div>
            <div className="step-sub">Mijozni yuzidan taning, qidiring yoki oxirgi mijozlardan birini tanlang</div>

            {/* AI Face Recognized Live Banner */}
            {faceRecognizedCustomer && (
              <div style={{
                background: 'linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)',
                border: '1.5px solid #10B981',
                borderRadius: '14px',
                padding: '12px 16px',
                marginBottom: '14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                boxShadow: '0 4px 14px rgba(16,185,129,0.15)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <img
                    src={faceRecognizedCustomer.image || '/static/images/default-avatar.png'}
                    alt=""
                    onError={(e) => { e.target.src = 'https://ui-avatars.com/api/?name=' + encodeURIComponent(faceRecognizedCustomer.name); }}
                    style={{ width: '44px', height: '44px', borderRadius: '10px', objectFit: 'cover', border: '2px solid #10B981' }}
                  />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#065F46' }}>
                      {faceRecognizedCustomer.name} (ID: {faceRecognizedCustomer.custom_id || faceRecognizedCustomer.id})
                    </div>
                    <div style={{ fontSize: '11px', color: '#047857', fontWeight: '600' }}>
                      Qarz: {Math.round(faceRecognizedCustomer.debt_amount || 0).toLocaleString()} so'm &bull; AI Kamera orqali tanildi ✨
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleConfirmCustomer(faceRecognizedCustomer)}
                  style={{
                    background: '#10B981',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 16px',
                    fontWeight: '800',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  Tanlash &rarr;
                </button>
              </div>
            )}
            
            <div className="search-row" style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
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
                title="Yangi mijoz qo'shish"
                style={{ width: '48px', height: '48px', borderRadius: '12px', background: '#1B6B4A', color: '#fff', border: 'none', fontSize: '20px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                +
              </button>
            </div>

            {/* Title for Recent Customers or Search Results */}
            <div style={{ fontSize: '13px', fontWeight: 'bold', color: searchQuery.trim() ? '#4B5563' : '#1B6B4A', marginBottom: '10px', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '6px' }}>
              {searchQuery.trim() ? (
                <span>🔍 Qidiruv natijalari:</span>
              ) : (
                <span>🕒 Oxirgi mijozlar (Tezkor tanlash):</span>
              )}
            </div>

            <div className="results-list" style={{ marginBottom: '16px', maxHeight: '340px', overflowY: 'auto' }}>
              {(Array.isArray(searchQuery.trim() ? customers : cachedCustomers) ? (searchQuery.trim() ? customers : cachedCustomers) : []).slice(0, visibleCustomersCount).map(c => {
                if (!c) return null;
                const debtNum = parseFloat(c.debt_amount) || 0;
                const limitNum = parseFloat(c.debt_limit) || 0;
                const scoreStr = typeof c.credit_score === 'string' ? c.credit_score : '';
                const cName = c.name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Mijoz';
                const cId = c.custom_id || c.id || '';
                return (
                  <div 
                    key={c.id || Math.random()} 
                    style={{ background: '#fff', border: '1.5px solid rgba(0,0,0,0.07)', borderRadius: '14px', padding: '12px 14px', marginBottom: '8px', cursor: 'pointer', transition: 'all 0.15s', boxShadow: '0 2px 6px rgba(0,0,0,0.02)' }}
                    onClick={() => handleConfirmCustomer(c)}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = '#1B6B4A'}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(0,0,0,0.07)'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', textAlign: 'left' }}>
                        <img 
                          src={c.image || '/static/images/default-avatar.png'} 
                          alt={cName} 
                          onError={(e) => { e.target.src = 'https://ui-avatars.com/api/?name=' + encodeURIComponent(cName); }}
                          style={{ width: '42px', height: '42px', borderRadius: '50%', objectFit: 'cover', border: '1px solid rgba(0,0,0,0.08)' }} 
                        />
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <span className="cust-name" style={{ fontWeight: 'bold', fontSize: '15px' }}>{cName}</span>
                            <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }} onClick={(e) => e.stopPropagation()}>
                              {/* Special Prices button */}
                              <button
                                type="button"
                                onClick={() => openPosCustomerSpecialPrices(c)}
                                title="Maxsus / Choyxona narxlarini sozlash"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '3px 8px',
                                  borderRadius: '8px',
                                  border: '1px solid #86EFAC',
                                  color: '#15803D',
                                  backgroundColor: '#DCFCE7',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  cursor: 'pointer'
                                }}
                              >
                                🏷️ Narxlar {Array.isArray(c.special_prices) && c.special_prices.length > 0 ? `(${c.special_prices.length})` : ''}
                              </button>

                              {/* Edit */}
                              <a 
                                href={"/pos/customers/?search=" + cId} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                title="Tahrirlash"
                                style={{ 
                                  display: 'inline-flex', 
                                  width: '28px', 
                                  height: '28px', 
                                  borderRadius: '8px', 
                                  border: '1px solid rgba(0,0,0,0.08)', 
                                  justifyContent: 'center', 
                                  alignItems: 'center', 
                                  color: '#B06000', 
                                  backgroundColor: 'rgba(212,168,83,0.08)',
                                  textDecoration: 'none'
                                }}
                              >
                                <i className="bi bi-pencil-fill" style={{ fontSize: '11px' }}></i>
                              </a>
                            </div>
                          </div>
                          <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: '600' }}>ID: {cId}</span>
                            {c.phone && <span>· {c.phone}</span>}
                            {scoreStr && (
                              <span style={{ 
                                background: scoreStr.startsWith('A') ? '#E6F4EA' : scoreStr.startsWith('B') ? '#E8F0FE' : scoreStr.startsWith('C') ? '#FEF7E0' : '#FCE8E6', 
                                color: scoreStr.startsWith('A') ? '#137333' : scoreStr.startsWith('B') ? '#1A73E8' : scoreStr.startsWith('C') ? '#B06000' : '#C5221F', 
                                padding: '1px 6px', 
                                borderRadius: '4px', 
                                fontSize: '10px', 
                                fontWeight: '800' 
                              }}>
                                AI Skoring: {scoreStr}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        {debtNum > 0 && (
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); openPosCustomerDebtHistory(c); }}
                            title="Barcha qarzlar tarixi va tafsilotlarini ko'rish"
                            className="debt-pill"
                            style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', padding: '4px 10px', color: '#DC3545', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          >
                            Qarz: {debtNum.toLocaleString('fr-FR')} so'm <i className="bi bi-clock-history"></i>
                          </button>
                        )}
                        {limitNum > 0 && (
                          <span style={{ fontSize: '10px', color: '#9CA3AF' }}>
                            Limit: {limitNum.toLocaleString('fr-FR')} so'm
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              {(searchQuery.trim() ? customers : cachedCustomers).length > visibleCustomersCount && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setVisibleCustomersCount(prev => prev + 10); }} 
                  style={{ width: '100%', padding: '10px', borderRadius: '10px', background: 'transparent', border: '1.5px solid #1B6B4A', color: '#1B6B4A', fontWeight: 'bold', cursor: 'pointer', margin: '10px 0' }}
                >
                  Yana yuklash...
                </button>
              )}
              {searchQuery.trim() && customers.length === 0 && (
                <div style={{ padding: '24px', textAlign: 'center', color: '#9CA3AF', background: '#fff', borderRadius: '14px' }}>
                  🔍 Ushbu so'rov bo'yicha mijoz topilmadi
                </div>
              )}
            </div>

            <button 
              className="btn-cash" 
              onClick={() => handleConfirmCustomer(null)}
              style={{ width: '100%', padding: '16px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', border: 'none', borderRadius: '14px', color: '#FFFFFF', fontWeight: '800', fontSize: '15px', cursor: 'pointer', marginBottom: '12px', boxShadow: '0 4px 14px rgba(27,107,74,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            >
              💵 Mijozsiz — Naqd pul
            </button>
            
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                className="btn-back" 
                onClick={() => setStep(1)}
                style={{ flex: 1, padding: '14px', background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '14px', color: '#334155', fontWeight: '800', fontSize: '14px', cursor: 'pointer', boxShadow: '0 2px 6px rgba(0,0,0,0.03)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
              >
                ← Orqaga
              </button>
              <button 
                type="button"
                onClick={resetTerminal}
                style={{ flex: 1, padding: '14px', background: '#FEF2F2', border: '1.5px solid #FECACA', borderRadius: '14px', color: '#DC2626', fontWeight: '800', fontSize: '14px', cursor: 'pointer', boxShadow: '0 2px 6px rgba(220,38,38,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
              >
                ✕ Bekor qilish
              </button>
            </div>
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
                  {selectedCustomer ? (selectedCustomer.name || selectedCustomer.first_name || 'Xaridor') : 'Nomalum xaridor'}
                </div>
              </div>
              <div className="confirm-card" style={{ flex: 1, background: '#F8F6F2', border: '1.5px solid rgba(0,0,0,0.07)', borderRadius: '14px', padding: '16px', textAlign: 'left' }}>
                <div className="confirm-card-lbl" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold' }}>Vazn</div>
                <div className="confirm-card-val" style={{ fontSize: '18px', fontWeight: '800', marginTop: '4px' }}>
                  {(typeof weight === 'number' ? weight : 0).toFixed(3)} kg
                </div>
              </div>
            </div>

            {/* Unit Price & Special Price & AI Advisor */}
            {selectedProduct && (
              <div style={{
                background: '#FFFFFF',
                border: '1.5px solid rgba(0,0,0,0.08)',
                borderRadius: '16px',
                padding: '14px 18px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '12px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
              }}>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: '#6B7280', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.5px' }}>
                      1 kg Narxi
                    </span>
                    {customUnitPrice !== null && (
                      <span style={{
                        fontSize: '11px',
                        background: '#DCFCE7',
                        color: '#15803D',
                        border: '1px solid #86EFAC',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        fontWeight: '800'
                      }}>
                        🏷️ Maxsus / Kelishilgan narx
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: '900', color: '#1B6B4A', fontFamily: 'monospace', marginTop: '2px' }}>
                    {((customUnitPrice !== null ? customUnitPrice : parseFloat(selectedProduct.price_per_kg)) || 0).toLocaleString('fr-FR')} <span style={{ fontSize: '14px', color: '#6B7280' }}>so'm / kg</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={handleEditUnitPricePrompt}
                    style={{
                      padding: '8px 14px',
                      borderRadius: '10px',
                      background: '#F3F4F6',
                      border: '1.5px solid #E5E7EB',
                      color: '#374151',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                    title="Narxni qo'lda tahrirlash (To'y-maraka uchun)"
                  >
                    ✏️ Narxni o'zgartirish
                  </button>

                  <button
                    type="button"
                    onClick={handleConsultDealAdvisor}
                    disabled={dealAdvisorLoading}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '10px',
                      background: 'linear-gradient(135deg, #4F46E5, #7C3AED)',
                      border: 'none',
                      color: '#FFFFFF',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)'
                    }}
                  >
                    <span>🤖</span> {dealAdvisorLoading ? 'Hisoblanmoqda...' : 'AI Qoplaydimi?'}
                  </button>
                </div>
              </div>
            )}

            {/* Quick Amounts Grid */}
            <div className="quick-amounts-wrap" style={{ marginBottom: '20px', textAlign: 'left' }}>
              <span className="quick-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                Summa tanlang
              </span>
              <div className="quick-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: '8px' }}>
                {(Array.isArray(quickAmounts) ? quickAmounts : []).map(amt => {
                  const amtNum = parseFloat(amt) || 0;
                  return (
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
                      {amtNum.toLocaleString('fr-FR')} so'm
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Payment Options */}
            <div style={{ textAlign: 'left', marginBottom: '20px' }}>
              <span className="pay-select-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                To'lov turi
              </span>
              <div className="pay-options" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  { id: 'naqd', label: '💵 Naqd' },
                  { id: 'karta', label: '💳 Karta' },
                  { id: 'qr', label: '📱 QR' },
                  { id: 'nasiya', label: '📋 Nasiya' },
                  { id: 'aralash', label: '🔀 Aralash' }
                ].map(item => (
                  <button 
                    key={item.id}
                    className={`pay-opt ${paymentMethod === item.id ? 'selected' : ''}`}
                    onClick={() => handlePaymentMethodChange(item.id)}
                    style={{
                      flex: item.id === 'aralash' ? '1 1 100%' : '1 1 calc(25% - 6px)',
                      padding: '12px 6px',
                      borderRadius: '12px',
                      border: '1.5px solid rgba(0,0,0,0.07)',
                      background: paymentMethod === item.id ? (item.id === 'aralash' ? 'linear-gradient(135deg, #4F46E5, #6366F1)' : 'linear-gradient(135deg, #1B6B4A, #2D9B6E)') : '#fff',
                      color: paymentMethod === item.id ? '#fff' : '#1A1A2E',
                      fontWeight: 'bold',
                      fontSize: '13px',
                      cursor: 'pointer'
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* SPLIT PAYMENT CONTROLS */}
            {paymentMethod === 'aralash' && (
              <div style={{ marginBottom: '20px', padding: '16px', background: '#F8FAFC', border: '1.5px solid #E2E8F0', borderRadius: '16px', textAlign: 'left' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', color: '#475569' }}>
                    🔀 Aralash To'lov Taqsimoti
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#1E293B' }}>
                    Jami: {selectedAmount.toLocaleString('fr-FR')} so'm
                  </span>
                </div>

                {/* Quick Split Buttons */}
                <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={() => {
                      const half = Math.round(selectedAmount / 2 / 1000) * 1000;
                      setSplitNaqd(half);
                      setSplitKarta(selectedAmount - half);
                      setSplitQr(0);
                      setSplitNasiya(0);
                    }}
                    style={{ padding: '6px 10px', fontSize: '11px', fontWeight: 'bold', borderRadius: '8px', background: '#EEF2FF', border: '1px solid #C7D2FE', color: '#4338CA', cursor: 'pointer' }}
                  >
                    50% Naqd + 50% Karta
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const cash = Math.min(100000, selectedAmount);
                      setSplitNaqd(cash);
                      setSplitKarta(selectedAmount - cash);
                      setSplitQr(0);
                      setSplitNasiya(0);
                    }}
                    style={{ padding: '6px 10px', fontSize: '11px', fontWeight: 'bold', borderRadius: '8px', background: '#EEF2FF', border: '1px solid #C7D2FE', color: '#4338CA', cursor: 'pointer' }}
                  >
                    100k Naqd + Qolgani Karta
                  </button>
                  {selectedCustomer && (
                    <button
                      type="button"
                      onClick={() => {
                        const cash = Math.min(100000, selectedAmount);
                        setSplitNaqd(cash);
                        setSplitKarta(0);
                        setSplitQr(0);
                        setSplitNasiya(selectedAmount - cash);
                      }}
                      style={{ padding: '6px 10px', fontSize: '11px', fontWeight: 'bold', borderRadius: '8px', background: '#FEF2F2', border: '1px solid #FECACA', color: '#DC2626', cursor: 'pointer' }}
                    >
                      100k Naqd + Qolgani Nasiya
                    </button>
                  )}
                </div>

                {/* Input Rows */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#047857', display: 'block', marginBottom: '4px' }}>
                      💵 Naqd pul:
                    </label>
                    <input
                      type="number"
                      step="1000"
                      min="0"
                      value={splitNaqd || ''}
                      onChange={(e) => setSplitNaqd(parseFloat(e.target.value) || 0)}
                      placeholder="0"
                      style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '14px', fontWeight: 'bold', boxSizing: 'border-box' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#2563EB', display: 'block', marginBottom: '4px' }}>
                      💳 Plastik karta:
                    </label>
                    <input
                      type="number"
                      step="1000"
                      min="0"
                      value={splitKarta || ''}
                      onChange={(e) => setSplitKarta(parseFloat(e.target.value) || 0)}
                      placeholder="0"
                      style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '14px', fontWeight: 'bold', boxSizing: 'border-box' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#D97706', display: 'block', marginBottom: '4px' }}>
                      📱 Yagona QR:
                    </label>
                    <input
                      type="number"
                      step="1000"
                      min="0"
                      value={splitQr || ''}
                      onChange={(e) => setSplitQr(parseFloat(e.target.value) || 0)}
                      placeholder="0"
                      style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '14px', fontWeight: 'bold', boxSizing: 'border-box' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#DC2626', display: 'block', marginBottom: '4px' }}>
                      📋 Nasiya (Qarz):
                    </label>
                    <input
                      type="number"
                      step="1000"
                      min="0"
                      disabled={!selectedCustomer}
                      value={splitNasiya || ''}
                      onChange={(e) => setSplitNasiya(parseFloat(e.target.value) || 0)}
                      placeholder={selectedCustomer ? "0" : "Mijoz tanlanmagan"}
                      style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '14px', fontWeight: 'bold', boxSizing: 'border-box', background: selectedCustomer ? '#fff' : '#F1F5F9' }}
                    />
                  </div>
                </div>

                {/* Split Status indicator */}
                {(() => {
                  const sumTotal = (parseFloat(splitNaqd) || 0) + (parseFloat(splitKarta) || 0) + (parseFloat(splitQr) || 0) + (parseFloat(splitNasiya) || 0);
                  const diff = selectedAmount - sumTotal;
                  const isExact = Math.abs(diff) < 50;

                  return (
                    <div style={{ padding: '10px 12px', borderRadius: '10px', background: isExact ? '#ECFDF5' : '#FEF2F2', border: `1px solid ${isExact ? '#A7F3D0' : '#FECACA'}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 'bold', color: isExact ? '#065F46' : '#991B1B' }}>
                        {isExact ? `✅ Taqsimlandi: ${sumTotal.toLocaleString('fr-FR')} so'm (To'liq)` : `⚠️ Taqsimlangan: ${sumTotal.toLocaleString('fr-FR')} so'm (Qolgan: ${diff.toLocaleString('fr-FR')} so'm)`}
                      </span>
                      {!isExact && diff > 0 && (
                        <button
                          type="button"
                          onClick={() => setSplitKarta(prev => prev + diff)}
                          style={{ padding: '4px 8px', fontSize: '11px', fontWeight: 'bold', borderRadius: '6px', background: '#2563EB', color: '#fff', border: 'none', cursor: 'pointer' }}
                        >
                          + Qolganini Kartaga qo'shish
                        </button>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}

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
              style={{ width: '100%', padding: '16px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '14px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', marginBottom: '10px' }}
            >
              {loadingSale ? 'Saqlanmoqda...' : 'Savdoni tasdiqlash'}
            </button>
            
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                className="btn-back" 
                onClick={() => setStep(2)}
                style={{ flex: 1, padding: '14px', background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '14px', color: '#334155', fontWeight: '800', fontSize: '14px', cursor: 'pointer', boxShadow: '0 2px 6px rgba(0,0,0,0.03)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
              >
                ← Orqaga
              </button>
              <button 
                type="button"
                onClick={resetTerminal}
                style={{ flex: 1, padding: '14px', background: '#FEF2F2', border: '1.5px solid #FECACA', borderRadius: '14px', color: '#DC2626', fontWeight: '800', fontSize: '14px', cursor: 'pointer', boxShadow: '0 2px 6px rgba(220,38,38,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
              >
                ✕ Bekor qilish
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: Thermal Receipt */}
        {step === 4 && receiptData && (
          <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div className="thermal-receipt" style={{ width: '100%', maxWidth: '360px', background: '#fff', padding: '24px', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 10px 30px rgba(0,0,0,0.05)', textAlign: 'left', marginBottom: '20px' }}>
              <div style={{ textAlign: 'center', marginBottom: '15px' }}>
                <h2 style={{ fontSize: '20px', fontWeight: '800', margin: '0 0 4px 0' }}>Baxmal Meat</h2>
                <div style={{ fontSize: '12px', color: '#6B7280' }}>Sifatli go'sht mahsulotlari</div>
                <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '2px' }}>Chek #{receiptData.sale_id}</div>
              </div>

              <div style={{ borderTop: '1px dashed #ccc', borderBottom: '1px dashed #ccc', padding: '12px 0', margin: '12px 0', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#6B7280' }}>Sana:</span>
                  <span style={{ fontWeight: '600' }}>{new Date().toLocaleDateString('uz-UZ')} {new Date().toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#6B7280' }}>Xaridor:</span>
                  <span style={{ fontWeight: '600' }}>{selectedCustomer ? selectedCustomer.name : "Noma'lum xaridor"}</span>
                </div>
                
                {paymentMethod === 'aralash' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginTop: '6px', paddingTop: '6px', borderTop: '1px dotted #e5e7eb' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#6B7280' }}>To'lov turi:</span>
                      <span style={{ fontWeight: '700', color: '#4F46E5' }}>🔀 ARALASH</span>
                    </div>
                    {receiptData.paid_naqd > 0 && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#047857' }}>
                        <span>• Naqd:</span>
                        <span style={{ fontWeight: '700' }}>{parseFloat(receiptData.paid_naqd).toLocaleString('fr-FR')} so'm</span>
                      </div>
                    )}
                    {receiptData.paid_karta > 0 && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#2563EB' }}>
                        <span>• Karta:</span>
                        <span style={{ fontWeight: '700' }}>{parseFloat(receiptData.paid_karta).toLocaleString('fr-FR')} so'm</span>
                      </div>
                    )}
                    {receiptData.paid_qr > 0 && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#D97706' }}>
                        <span>• QR:</span>
                        <span style={{ fontWeight: '700' }}>{parseFloat(receiptData.paid_qr).toLocaleString('fr-FR')} so'm</span>
                      </div>
                    )}
                    {receiptData.debt_added > 0 && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#DC2626' }}>
                        <span>• Nasiya (qarz):</span>
                        <span style={{ fontWeight: '700' }}>{parseFloat(receiptData.debt_added).toLocaleString('fr-FR')} so'm</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#6B7280' }}>To'lov turi:</span>
                    <span style={{ fontWeight: '600', textTransform: 'uppercase' }}>{paymentMethod}</span>
                  </div>
                )}
              </div>

              <div style={{ marginBottom: '15px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', fontWeight: 'bold', marginBottom: '4px' }}>
                  <span>{selectedProduct ? selectedProduct.name : 'Mahsulot'}</span>
                  <span>{selectedAmount.toLocaleString('fr-FR')} so'm</span>
                </div>
                <div style={{ fontSize: '12px', color: '#6B7280' }}>
                  {weight.toFixed(3)} kg × {selectedProduct ? parseFloat(selectedProduct.price_per_kg).toLocaleString('fr-FR') : 0} so'm
                </div>
              </div>

              <div style={{ borderTop: '1px solid #eee', paddingTop: '10px', marginBottom: '15px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', fontWeight: '800' }}>
                  <span>Jami:</span>
                  <span>{selectedAmount.toLocaleString('fr-FR')} so'm</span>
                </div>
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
                style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: numpadMode === 'kg' ? '#1B6B4A' : 'transparent', color: numpadMode === 'kg' ? '#fff' : '#6B7280', fontWeight: 'bold', cursor: 'pointer' }}
                onClick={() => { setNumpadMode('kg'); setNumpadBuffer(''); }}
              >
                Vazn (kg)
              </button>
              <button 
                id="mode-sum"
                style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: numpadMode === 'sum' ? '#1B6B4A' : 'transparent', color: numpadMode === 'sum' ? '#fff' : '#6B7280', fontWeight: 'bold', cursor: 'pointer' }}
                onClick={() => { setNumpadMode('sum'); setNumpadBuffer(''); }}
              >
                Summa (so'm)
              </button>
            </div>

            {/* Smart warning & One-Click conversion if huge kg number entered */}
            {numpadMode === 'kg' && parseFloat(numpadBuffer || '0') >= 100 && (
              <div style={{
                background: '#FFFBEB',
                border: '1.5px solid #F59E0B',
                borderRadius: '12px',
                padding: '10px',
                marginBottom: '12px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#B45309', marginBottom: '4px' }}>
                  ⚠️ Diqqat: {parseFloat(numpadBuffer).toLocaleString('fr-FR')} kg kiritildi!
                </div>
                <div style={{ fontSize: '11px', color: '#78350F', marginBottom: '6px' }}>
                  Agar bu pul summasi bo'lsa, bitta bosishda so'mga o'tkazing:
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const sumVal = parseInt(numpadBuffer) || 0;
                    if (selectedProduct && sumVal > 0) {
                      const price = parseFloat(selectedProduct.price_per_kg);
                      const calcKg = (sumVal / price);
                      setWeight(parseFloat(calcKg.toFixed(3)));
                      setSelectedAmount(sumVal);
                      setNumpadOpen(false);
                    } else {
                      setNumpadMode('sum');
                    }
                  }}
                  style={{
                    background: '#F59E0B',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '6px 14px',
                    fontWeight: 'bold',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  🔄 {parseInt(numpadBuffer || '0').toLocaleString('fr-FR')} so'm deb hisoblash
                </button>
              </div>
            )}

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

            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                type="button"
                onClick={() => {
                  setNumpadBuffer('');
                  setWeight(0.000);
                  setNumpadOpen(false);
                }}
                style={{ flex: 1, padding: '14px', background: '#FEF2F2', color: '#DC3545', border: '1.5px solid #FCA5A5', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                ❌ 0 kg (Tozalash)
              </button>
              <button 
                type="button"
                onClick={handleNumpadConfirm}
                style={{ flex: 1.5, padding: '14px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Kiritish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ════════════ ADD CUSTOMER MODAL ════════════ */}
      {showAddCustomer && (
        <div className="numpad-overlay open" style={{ zIndex: 10000 }}>
          <div className="numpad-box" style={{ background: '#fff', padding: '24px', borderRadius: '24px', width: '90%', maxWidth: '420px', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 10px 40px rgba(0,0,0,0.15)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
              <span className="modal-title" style={{ fontWeight: 'bold', color: '#1A1A2E', fontSize: '17px' }}>👤 Yangi mijoz qo'shish</span>
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
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none', boxSizing: 'border-box' }}
              />
            </div>
            
            <div style={{ textAlign: 'left', marginBottom: '12px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Familiyasi</label>
              <input 
                type="text" 
                className="mf-input" 
                placeholder="Karimov (ixtiyoriy)"
                value={custLastName}
                onChange={(e) => setCustLastName(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none', boxSizing: 'border-box' }}
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
                style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none', boxSizing: 'border-box' }}
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

            <div style={{ textAlign: 'left', marginBottom: '14px' }}>
              <label className="mf-label" style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>Mijoz ID *</label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input 
                  type="text" 
                  className="mf-input" 
                  placeholder="Masalan: 01"
                  value={custCustomId}
                  onChange={(e) => setCustCustomId(e.target.value)}
                  style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1.5px solid rgba(0,0,0,0.07)', background: '#F8F6F2', outline: 'none', boxSizing: 'border-box' }}
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

            <div style={{ textAlign: 'left', marginBottom: '16px' }}>
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

            {/* Special / Choyxona Prices section */}
            <div style={{
              background: '#F0FDF4',
              border: '1.5px solid #BBF7D0',
              borderRadius: '14px',
              padding: '14px',
              marginBottom: '20px',
              textAlign: 'left'
            }}>
              <div style={{ fontSize: '13px', fontWeight: '800', color: '#15803D', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>🏷️</span> Maxsus Narxlar (Choyxona / VIP)
              </div>
              <p style={{ fontSize: '11px', color: '#4B5563', margin: '0 0 10px 0', lineHeight: '1.4' }}>
                Ushbu mijozga doimiy arzonlashtirilgan narx belgilamoqchi bo'lsangiz, tegishli qatorga maxsus narxni kiriting:
              </p>

              {(Array.isArray(products) ? products : []).map(p => (
                <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', gap: '8px' }}>
                  <div style={{ fontSize: '12px', color: '#1F2937', fontWeight: '600', flex: 1.4 }}>
                    🥩 {p.name}
                    <span style={{ display: 'block', fontSize: '10px', color: '#6B7280', fontFamily: 'monospace' }}>
                      (Standart: {parseFloat(p.price_per_kg).toLocaleString('fr-FR')} so'm)
                    </span>
                  </div>
                  <input
                    type="number"
                    placeholder="Maxsus narx"
                    value={newCustSpecialPrices[p.id] || ''}
                    onChange={(e) => setNewCustSpecialPrices({ ...newCustSpecialPrices, [p.id]: e.target.value })}
                    style={{
                      width: '130px',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: '1.5px solid #86EFAC',
                      background: '#fff',
                      fontSize: '12px',
                      fontFamily: 'monospace',
                      fontWeight: 'bold',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              ))}
            </div>

            <button 
              className="btn-save-cust" 
              onClick={handleSaveCustomer}
              style={{ width: '100%', padding: '14px', background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', fontSize: '14px', cursor: 'pointer', boxShadow: '0 4px 12px rgba(27,107,74,0.3)' }}
            >
              Saqlash va Tanlash
            </button>
          </div>
        </div>
      )}

      {/* ════════════ POS CUSTOMER SPECIAL PRICES MODAL ════════════ */}
      {posSpModalOpen && posSpCustomer && (
        <div className="numpad-overlay open" style={{ zIndex: 10000 }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '24px',
            maxWidth: '520px',
            width: '90%',
            maxHeight: '90vh',
            overflowY: 'auto',
            boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
            textAlign: 'left'
          }}>
            {/* Header */}
            <div style={{
              background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)',
              color: '#FFFFFF',
              padding: '18px 22px',
              borderRadius: '24px 24px 0 0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800' }}>
                  🏷️ Maxsus Narxlar: {posSpCustomer.name || posSpCustomer.first_name}
                </h4>
                <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.8)' }}>
                  ID: {posSpCustomer.custom_id || posSpCustomer.id}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setPosSpModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '20px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: '20px' }}>
              <p style={{ fontSize: '12px', color: '#6B7280', marginBottom: '14px' }}>
                Ushbu mijoz tanlanganda ushbu mahsulotlarga avtomatik arzonlashtirilgan narx qo'llanadi.
              </p>

              {/* List of active special prices */}
              <div style={{ border: '1px solid #E5E7EB', borderRadius: '12px', overflow: 'hidden', marginBottom: '16px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead style={{ background: '#F9FAFB', color: '#6B7280', fontSize: '11px', textTransform: 'uppercase' }}>
                    <tr>
                      <th style={{ padding: '8px 12px' }}>Mahsulot</th>
                      <th style={{ padding: '8px 8px' }}>Standart</th>
                      <th style={{ padding: '8px 8px' }}>Kelishilgan</th>
                      <th style={{ padding: '8px 8px', textAlign: 'right' }}>O'chirish</th>
                    </tr>
                  </thead>
                  <tbody>
                    {posSpList.map(sp => (
                      <tr key={sp.id} style={{ borderTop: '1px solid #F3F4F6' }}>
                        <td style={{ padding: '8px 12px', fontWeight: '700' }}>🥩 {sp.product_name}</td>
                        <td style={{ padding: '8px 8px', color: '#6B7280', fontFamily: 'monospace' }}>
                          {Math.round(sp.standard_price).toLocaleString('fr-FR')}
                        </td>
                        <td style={{ padding: '8px 8px', color: '#15803D', fontWeight: '800', fontFamily: 'monospace' }}>
                          {Math.round(sp.special_price).toLocaleString('fr-FR')} so'm
                        </td>
                        <td style={{ padding: '8px 8px', textAlign: 'right' }}>
                          <button
                            type="button"
                            onClick={() => handleDeletePosSpecialPrice(sp.id)}
                            style={{ background: '#FEE2E2', color: '#DC2626', border: 'none', borderRadius: '50%', width: '24px', height: '24px', cursor: 'pointer', fontWeight: 'bold' }}
                          >
                            ×
                          </button>
                        </td>
                      </tr>
                    ))}
                    {posSpList.length === 0 && (
                      <tr>
                        <td colSpan="4" style={{ padding: '16px', textAlign: 'center', color: '#9CA3AF' }}>
                          Hozircha maxsus narx yo'q (Standart narxlarda oladi)
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Add form */}
              <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '14px', padding: '14px' }}>
                <div style={{ fontSize: '12px', fontWeight: '800', color: '#15803D', marginBottom: '8px' }}>
                  ➕ Yangi maxsus narx qo'shish
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr auto', gap: '8px', alignItems: 'center' }}>
                  <select
                    value={posSpSelectedProduct}
                    onChange={(e) => setPosSpSelectedProduct(e.target.value)}
                    style={{ padding: '8px', borderRadius: '8px', border: '1px solid #D1D5DB', fontSize: '12px', background: '#fff' }}
                  >
                    <option value="">-- Mahsulot --</option>
                    {(Array.isArray(products) ? products : []).map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({parseFloat(p.price_per_kg).toLocaleString('fr-FR')})</option>
                    ))}
                  </select>

                  <input
                    type="number"
                    placeholder="Narx (so'm)"
                    value={posSpPriceInput}
                    onChange={(e) => setPosSpPriceInput(e.target.value)}
                    style={{ padding: '8px', borderRadius: '8px', border: '1px solid #D1D5DB', fontSize: '12px', fontFamily: 'monospace', fontWeight: 'bold', background: '#fff' }}
                  />

                  <button
                    type="button"
                    onClick={handleSavePosSpecialPrice}
                    style={{ padding: '8px 14px', borderRadius: '8px', background: '#1B6B4A', color: '#fff', border: 'none', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer' }}
                  >
                    Saqlash
                  </button>
                </div>
              </div>

              <div style={{ marginTop: '16px', textAlign: 'right' }}>
                <button
                  type="button"
                  onClick={() => setPosSpModalOpen(false)}
                  style={{ padding: '10px 20px', borderRadius: '10px', background: '#F3F4F6', border: '1px solid #D1D5DB', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer' }}
                >
                  Yopish
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ════════════ POS CUSTOMER DEBT HISTORY MODAL ════════════ */}
      {posDebtHistModalOpen && posDebtHistCustomer && (
        <div className="numpad-overlay open" style={{ zIndex: 10005 }}>
          <div style={{ background: '#fff', borderRadius: '24px', width: '95%', maxWidth: '640px', boxShadow: '0 25px 60px rgba(0,0,0,0.3)', overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: '90vh' }}>
            {/* Header */}
            <div style={{ background: 'linear-gradient(135deg, #1E293B, #0F172A)', color: '#fff', padding: '18px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#F87171', borderRadius: '8px', padding: '3px 8px', fontSize: '11px' }}>📋 Qarz Tarixi</span>
                  <span>{posDebtHistCustomer.first_name} {posDebtHistCustomer.last_name || ''}</span>
                </h4>
                <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '2px' }}>
                  ID: {posDebtHistCustomer.custom_id || posDebtHistCustomer.id} · Tel: {posDebtHistCustomer.phone || '—'}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setPosDebtHistModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '22px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Summary badges */}
            {posDebtHistData && posDebtHistData.summary && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', padding: '12px 20px', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px', padding: '8px 10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#DC2626' }}>🔴 JAMI QARZ OLINGAN</div>
                  <div style={{ fontSize: '14px', fontWeight: '800', color: '#991B1B', marginTop: '2px' }}>
                    {Math.round(posDebtHistData.summary.total_debt_taken || 0).toLocaleString('fr-FR')} so'm
                  </div>
                </div>
                <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '12px', padding: '8px 10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#16A34A' }}>🟢 JAMI TO'LANGAN</div>
                  <div style={{ fontSize: '14px', fontWeight: '800', color: '#166534', marginTop: '2px' }}>
                    {Math.round(posDebtHistData.summary.total_debt_paid || 0).toLocaleString('fr-FR')} so'm
                  </div>
                </div>
                <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '12px', padding: '8px 10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#2563EB' }}>💳 HOZIRGI QOLDIQ</div>
                  <div style={{ fontSize: '14px', fontWeight: '800', color: '#1E40AF', marginTop: '2px' }}>
                    {Math.round(posDebtHistData.summary.current_balance || 0).toLocaleString('fr-FR')} so'm
                  </div>
                </div>
              </div>
            )}

            {/* List */}
            <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1, maxHeight: '420px', background: '#FFFFFF' }}>
              {posDebtHistLoading ? (
                <div style={{ textAlign: 'center', padding: '30px', color: '#94A3B8' }}>
                  <div className="spinner" style={{ margin: '0 auto 10px' }}></div>
                  <div>Tafsilotlar yuklanmoqda...</div>
                </div>
              ) : posDebtHistData && posDebtHistData.timeline && posDebtHistData.timeline.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {posDebtHistData.timeline.map((item, idx) => {
                    const isDebt = item.type === 'debt_add';
                    const amtFormatted = Math.abs(Math.round(item.amount)).toLocaleString('fr-FR');
                    return (
                      <div key={idx} style={{ border: '1px solid #E2E8F0', borderRadius: '12px', padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                            <span style={{ background: isDebt ? '#FEF2F2' : '#F0FDF4', color: isDebt ? '#DC2626' : '#16A34A', fontSize: '10px', fontWeight: 'bold', padding: '2px 6px', borderRadius: '6px' }}>
                              {item.badge}
                            </span>
                            <span style={{ fontSize: '11px', color: '#64748B' }}>🕒 {item.created_at}</span>
                          </div>
                          <div style={{ fontWeight: '700', fontSize: '13px', color: '#1E293B' }}>{item.title}</div>
                          <div style={{ fontSize: '12px', color: '#475569', marginTop: '2px' }}>{item.note}</div>
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          <div style={{ fontSize: '15px', fontWeight: '800', color: isDebt ? '#DC2626' : '#16A34A', fontFamily: 'monospace' }}>
                            {isDebt ? '+' : '-'}{amtFormatted} so'm
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: '#9CA3AF' }}>
                  <div>🛡️ Hech qanday qarz yoki to'lov tarixi topilmadi</div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{ padding: '12px 20px', background: '#F8FAFC', borderTop: '1px solid #E2E8F0', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setPosDebtHistModalOpen(false)}
                style={{ padding: '8px 18px', borderRadius: '10px', background: '#64748B', color: '#fff', border: 'none', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer' }}
              >
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ════════════ KASSA SMENASI MODAL ════════════ */}
      {shiftModalOpen && (
        <div className="numpad-overlay open" style={{ zIndex: 10000 }}>
          <div style={{ background: '#fff', padding: '24px', borderRadius: '24px', width: '90%', maxWidth: '480px', boxShadow: '0 20px 60px rgba(0,0,0,0.25)', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '18px', fontWeight: '800', color: '#1A1A2E' }}>
                {shiftData.is_open ? `📊 Smena #${shiftData.shift_id} (Kassa Boshqaruvi)` : '🔓 Yangi Kassa Smenasini Ochish'}
              </div>
              <button onClick={() => setShiftModalOpen(false)} style={{ background: 'transparent', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#9CA3AF' }}>✕</button>
            </div>

            {/* ── CASE 1: SMENA OCHISH ── */}
            {!shiftData.is_open ? (
              <form onSubmit={handleOpenShiftSubmit}>
                <p style={{ fontSize: '13px', color: '#6B7280', marginBottom: '16px', lineHeight: '1.4' }}>
                  Ertalabki savdo boshida kassa g'aladonidagi mayda naqd pulni kiriting.
                </p>

                <div style={{ marginBottom: '14px' }}>
                  <label style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '6px', display: 'block' }}>
                    Boshlang'ich Naqd Pul (so'm) *
                  </label>
                  <input 
                    type="number"
                    value={shiftOpeningCash}
                    onChange={(e) => setShiftOpeningCash(e.target.value)}
                    placeholder="0"
                    style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '2px solid #10B981', fontSize: '20px', fontWeight: 'bold', color: '#1B6B4A', background: '#F0FDF4', outline: 'none', boxSizing: 'border-box' }}
                    autoFocus
                  />
                </div>

                {/* Quick Chips */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  {[0, 100000, 200000, 300000, 500000, 1000000].map(amt => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setShiftOpeningCash(amt.toString())}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '8px',
                        background: parseFloat(shiftOpeningCash) === amt ? '#10B981' : '#F3F4F6',
                        color: parseFloat(shiftOpeningCash) === amt ? '#fff' : '#4B5563',
                        border: 'none',
                        fontSize: '12px',
                        fontWeight: '600',
                        cursor: 'pointer'
                      }}
                    >
                      {amt === 0 ? "0 so'm" : `${(amt / 1000).toLocaleString('fr-FR')}k`}
                    </button>
                  ))}
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <label style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '6px', display: 'block' }}>
                    Smena izohi (Ixtiyoriy)
                  </label>
                  <input 
                    type="text"
                    value={shiftNotes}
                    onChange={(e) => setShiftNotes(e.target.value)}
                    placeholder="Masalan: 1-kassir Dilshod navbatchiligi"
                    style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1.5px solid rgba(0,0,0,0.1)', fontSize: '13px', background: '#F9FAFB', outline: 'none', boxSizing: 'border-box' }}
                  />
                </div>

                <button 
                  type="submit"
                  disabled={loadingShift}
                  style={{ width: '100%', padding: '16px', background: 'linear-gradient(135deg, #10B981, #059669)', color: '#fff', border: 'none', borderRadius: '14px', fontSize: '16px', fontWeight: '800', cursor: 'pointer', boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)' }}
                >
                  {loadingShift ? 'Ochilmoqda...' : '🚀 Smenani Boshlash'}
                </button>
              </form>
            ) : (
              /* ── CASE 2: SMENA FAOL & YOPISH ── */
              <form onSubmit={handleCloseShiftSubmit}>
                <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '14px' }}>
                  👤 Kassir: <b>{shiftData.cashier_name || 'Admin'}</b> • ⏱ Ochilgan: <b>{shiftData.opened_at}</b>
                </div>

                {/* Smena Stats Summary */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginBottom: '16px' }}>
                  <div style={{ background: '#F9FAFB', padding: '10px 12px', borderRadius: '10px', border: '1px solid #E5E7EB' }}>
                    <div style={{ fontSize: '11px', color: '#6B7280' }}>💰 Boshlang'ich kassa:</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#1F2937' }}>{(shiftData.opening_cash || 0).toLocaleString('fr-FR')} so'm</div>
                  </div>
                  <div style={{ background: '#F0FDF4', padding: '10px 12px', borderRadius: '10px', border: '1px solid #BBF7D0' }}>
                    <div style={{ fontSize: '11px', color: '#15803D' }}>💵 Naqd savdolar:</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#166534' }}>{(shiftData.cash_sales || 0).toLocaleString('fr-FR')} so'm</div>
                  </div>
                  <div style={{ background: '#EFF6FF', padding: '10px 12px', borderRadius: '10px', border: '1px solid #BFDBFE' }}>
                    <div style={{ fontSize: '11px', color: '#1D4ED8' }}>💳 Karta savdolar:</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#1E40AF' }}>{(shiftData.card_sales || 0).toLocaleString('fr-FR')} so'm</div>
                  </div>
                  <div style={{ background: '#FFFBEB', padding: '10px 12px', borderRadius: '10px', border: '1px solid #FDE68A' }}>
                    <div style={{ fontSize: '11px', color: '#B45309' }}>📱 QR savdolar:</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#92400E' }}>{(shiftData.qr_sales || 0).toLocaleString('fr-FR')} so'm</div>
                  </div>
                  <div style={{ background: '#FEF2F2', padding: '10px 12px', borderRadius: '10px', border: '1px solid #FECACA' }}>
                    <div style={{ fontSize: '11px', color: '#DC2626' }}>📋 Nasiya (qarz):</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#991B1B' }}>{(shiftData.debt_sales || 0).toLocaleString('fr-FR')} so'm</div>
                  </div>
                  <div style={{ background: '#FAF5FF', padding: '10px 12px', borderRadius: '10px', border: '1px solid #E9D5FF' }}>
                    <div style={{ fontSize: '11px', color: '#7E22CE' }}>🧾 Jami cheklar:</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#6B21A8' }}>{shiftData.sales_count || 0} ta</div>
                  </div>
                </div>

                {/* Expected Cash Banner */}
                <div style={{ background: '#EEF2FF', border: '1.5px solid #C7D2FE', borderRadius: '14px', padding: '12px 14px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '11px', color: '#4F46E5', fontWeight: 'bold', textTransform: 'uppercase' }}>G'aladonda kutilayotgan naqd pul:</div>
                    <div style={{ fontSize: '18px', fontWeight: '900', color: '#3730A3' }}>{(shiftData.expected_cash || 0).toLocaleString('fr-FR')} so'm</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShiftActualCash(shiftData.expected_cash?.toString() || '0')}
                    style={{ background: '#4F46E5', color: '#fff', border: 'none', borderRadius: '8px', padding: '6px 12px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
                  >
                    Nusxa olish 📋
                  </button>
                </div>

                {/* Actual Cash Input */}
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '6px', display: 'block' }}>
                    Faktik g'aladondagi naqd pul (Sanab kiritiladi) *
                  </label>
                  <input 
                    type="number"
                    value={shiftActualCash}
                    onChange={(e) => setShiftActualCash(e.target.value)}
                    placeholder="0"
                    style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '2px solid #3B82F6', fontSize: '20px', fontWeight: 'bold', color: '#1E40AF', background: '#EFF6FF', outline: 'none', boxSizing: 'border-box' }}
                    autoFocus
                  />
                </div>

                {/* Live Difference Badge */}
                {shiftActualCash !== '' && (
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: '10px',
                    marginBottom: '16px',
                    fontSize: '13px',
                    fontWeight: 'bold',
                    textAlign: 'center',
                    background: (parseFloat(shiftActualCash) - (shiftData.expected_cash || 0)) === 0 
                      ? '#DCFCE7' 
                      : (parseFloat(shiftActualCash) - (shiftData.expected_cash || 0)) > 0 
                      ? '#FEF3C7' 
                      : '#FEE2E2',
                    color: (parseFloat(shiftActualCash) - (shiftData.expected_cash || 0)) === 0 
                      ? '#166534' 
                      : (parseFloat(shiftActualCash) - (shiftData.expected_cash || 0)) > 0 
                      ? '#92400E' 
                      : '#991B1B',
                    border: '1px solid currentColor'
                  }}>
                    {(parseFloat(shiftActualCash) - (shiftData.expected_cash || 0)) === 0 ? (
                      "✅ Kassa aniq to'g'ri (Farq: 0 so'm)"
                    ) : (parseFloat(shiftActualCash) - (shiftData.expected_cash || 0)) > 0 ? (
                      `ℹ️ Ortiqcha pul: +${(parseFloat(shiftActualCash) - shiftData.expected_cash).toLocaleString('fr-FR')} so'm`
                    ) : (
                      `⚠️ Kamomad: ${(parseFloat(shiftActualCash) - shiftData.expected_cash).toLocaleString('fr-FR')} so'm`
                    )}
                  </div>
                )}

                <div style={{ marginBottom: '20px' }}>
                  <label style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '6px', display: 'block' }}>
                    Shift yakuni izohi
                  </label>
                  <input 
                    type="text"
                    value={shiftNotes}
                    onChange={(e) => setShiftNotes(e.target.value)}
                    placeholder="Masalan: Kun muvaffaqiyatli yakunlandi"
                    style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1.5px solid rgba(0,0,0,0.1)', fontSize: '13px', background: '#F9FAFB', outline: 'none', boxSizing: 'border-box' }}
                  />
                </div>

                <button 
                  type="submit"
                  disabled={loadingShift}
                  style={{ width: '100%', padding: '16px', background: 'linear-gradient(135deg, #DC2626, #B91C1C)', color: '#fff', border: 'none', borderRadius: '14px', fontSize: '16px', fontWeight: '800', cursor: 'pointer', boxShadow: '0 4px 14px rgba(220, 38, 38, 0.35)' }}
                >
                  {loadingShift ? 'Yopilmoqda...' : '🔒 Smenani Yopish va Z-Hisobot Chiqarish'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ════════════ Z-REPORT THERMAL RECEIPT SLIP MODAL ════════════ */}
      {zReportData && (
        <div className="numpad-overlay open" style={{ zIndex: 10001 }}>
          <div style={{ background: '#fff', padding: '24px', borderRadius: '24px', width: '90%', maxWidth: '380px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ textAlign: 'center', marginBottom: '14px' }}>
              <div style={{ fontSize: '20px', fontWeight: '900', color: '#1B6B4A', letterSpacing: '1px' }}>BAXMAL MEAT</div>
              <div style={{ fontSize: '13px', fontWeight: '800', color: '#111827', marginTop: '2px' }}>KASSA Z-HISOBOTI</div>
              <div style={{ fontSize: '11px', color: '#6B7280' }}>Smena #{zReportData.shift_id}</div>
            </div>

            <div style={{ borderTop: '1px dashed #CBD5E1', borderBottom: '1px dashed #CBD5E1', padding: '10px 0', fontSize: '12px', marginBottom: '12px', lineHeight: '1.6' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#6B7280' }}>Kassir:</span>
                <span style={{ fontWeight: 'bold' }}>{zReportData.cashier_name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#6B7280' }}>Ochilgan:</span>
                <span>{zReportData.opened_at}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#6B7280' }}>Yopilgan:</span>
                <span>{zReportData.closed_at}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#6B7280' }}>Cheklar soni:</span>
                <span style={{ fontWeight: 'bold' }}>{zReportData.sales_count} ta</span>
              </div>
            </div>

            <div style={{ fontSize: '12px', marginBottom: '14px', lineHeight: '1.7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Boshlang'ich kassa:</span>
                <b>{zReportData.opening_cash.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#166534' }}>
                <span>Naqd savdo:</span>
                <b>+{zReportData.cash_sales.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#1E40AF' }}>
                <span>Karta savdo:</span>
                <b>+{zReportData.card_sales.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#92400E' }}>
                <span>QR savdo:</span>
                <b>+{zReportData.qr_sales.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#991B1B' }}>
                <span>Nasiya (qarz):</span>
                <b>{zReportData.debt_sales.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #E5E7EB', paddingTop: '4px', marginTop: '4px' }}>
                <span style={{ fontWeight: '800' }}>Kutilgan naqd:</span>
                <b style={{ color: '#4F46E5' }}>{zReportData.expected_cash.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: '800' }}>Faktik naqd:</span>
                <b>{zReportData.actual_cash.toLocaleString('fr-FR')} so'm</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '900', color: zReportData.difference === 0 ? '#166534' : zReportData.difference > 0 ? '#92400E' : '#DC2626' }}>
                <span>Farq:</span>
                <span>{zReportData.difference === 0 ? "0 so'm (To'liq)" : `${zReportData.difference > 0 ? '+' : ''}${zReportData.difference.toLocaleString('fr-FR')} so'm`}</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => window.print()}
                style={{ flex: 1, padding: '12px', background: '#1B6B4A', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer' }}
              >
                🖨️ Chop etish
              </button>
              <button
                type="button"
                onClick={() => setZReportData(null)}
                style={{ flex: 1, padding: '12px', background: '#F3F4F6', color: '#4B5563', border: 'none', borderRadius: '12px', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer' }}
              >
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ════════════ SOVUQXONA & VITRINA NAZORATI MODAL ════════════ */}
      {batchModalOpen && (
        <div className="numpad-overlay open" style={{ zIndex: 10000 }}>
          <div style={{ background: '#fff', padding: '24px', borderRadius: '24px', width: '90%', maxWidth: '580px', boxShadow: '0 20px 60px rgba(0,0,0,0.25)', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <div style={{ fontSize: '18px', fontWeight: '800', color: '#1A1A2E' }}>🥩 Vitrina & Sovuqxona Nazorati</div>
                <div style={{ fontSize: '12px', color: '#6B7280' }}>Go'sht partiyalarining muddati va AI tavsiyalari</div>
              </div>
              <button onClick={() => setBatchModalOpen(false)} style={{ background: 'transparent', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#9CA3AF' }}>✕</button>
            </div>

            {/* Summary Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '16px' }}>
              <div style={{ background: '#F9FAFB', padding: '10px', borderRadius: '12px', border: '1px solid #E5E7EB', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#6B7280' }}>Jami Partiyalar</div>
                <div style={{ fontSize: '16px', fontWeight: '800', color: '#111827' }}>{batchesData?.summary?.active_batches_count || 0} ta</div>
              </div>
              <div style={{ background: '#FEF3C7', padding: '10px', borderRadius: '12px', border: '1px solid #FDE68A', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#92400E' }}>Ogohlantirish (2 kun)</div>
                <div style={{ fontSize: '16px', fontWeight: '800', color: '#B45309' }}>{batchesData?.summary?.warning_count || 0} ta</div>
              </div>
              <div style={{ background: '#FEE2E2', padding: '10px', borderRadius: '12px', border: '1px solid #FECACA', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#991B1B' }}>Qurish Xavfi (3+ kun)</div>
                <div style={{ fontSize: '16px', fontWeight: '800', color: '#DC2626' }}>{batchesData?.summary?.critical_count || 0} ta</div>
              </div>
            </div>

            {/* Batches List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
              {(batchesData?.batches || []).map(b => (
                <div 
                  key={b.id}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '14px',
                    border: '1.5px solid ' + (b.status_tag === 'critical' ? '#FCA5A5' : (b.status_tag === 'warning' ? '#FDE68A' : '#E5E7EB')),
                    background: b.status_tag === 'critical' ? '#FEF2F2' : (b.status_tag === 'warning' ? '#FFFBEB' : '#F9FAFB')
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ fontWeight: '800', fontSize: '14px', color: '#111827' }}>
                      {b.product_name} <span style={{ fontSize: '12px', color: '#6B7280', fontWeight: 'normal' }}>(Partiya #{b.id})</span>
                    </div>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: '800',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      background: b.status_tag === 'critical' ? '#DC2626' : (b.status_tag === 'warning' ? '#D97706' : '#10B981'),
                      color: '#fff'
                    }}>
                      {b.status_label}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#4B5563', marginBottom: '6px' }}>
                    <span>📦 Qoldiq: <b>{b.current_quantity.toFixed(2)} kg</b> (Dastlabki: {b.initial_quantity.toFixed(2)} kg)</span>
                    <span style={{ color: '#DC2626' }}>📉 Qurish: -{b.loss_kg.toFixed(3)} kg</span>
                  </div>

                  {b.ai_recommendation && (
                    <div style={{
                      background: 'rgba(255,255,255,0.7)',
                      border: '1px dashed ' + (b.status_tag === 'critical' ? '#EF4444' : '#F59E0B'),
                      padding: '8px 10px',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: b.status_tag === 'critical' ? '#991B1B' : '#92400E',
                      lineHeight: '1.4'
                    }}>
                      💡 <b>AI Tavsiya:</b> {b.ai_recommendation}
                    </div>
                  )}
                </div>
              ))}

              {(!batchesData?.batches || batchesData.batches.length === 0) && (
                <div style={{ textAlign: 'center', padding: '30px 10px', color: '#9CA3AF', fontSize: '13px' }}>
                  Hozirda faol go'sht partiyalari mavjud emas.
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <a
                href="/pos/batch-report/"
                target="_blank"
                rel="noreferrer"
                style={{ flex: 1, padding: '12px', background: '#EEF2FF', color: '#4F46E5', borderRadius: '12px', fontWeight: 'bold', fontSize: '13px', textAlign: 'center', textDecoration: 'none', border: '1px solid #C7D2FE' }}
              >
                📊 To'liq Zaxira Tahlili
              </a>
              <button
                type="button"
                onClick={() => setBatchModalOpen(false)}
                style={{ flex: 1, padding: '12px', background: '#1B6B4A', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer' }}
              >
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI DEAL ADVISOR MODAL (QOPLAYDIMI?) */}
      {dealAdvisorModalOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 99999,
          padding: '20px'
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '24px',
            maxWidth: '520px',
            width: '100%',
            overflow: 'hidden',
            boxShadow: '0 24px 60px rgba(0,0,0,0.3)',
            animation: 'fadeUp 0.25s ease-out'
          }}>
            {/* Modal Header */}
            <div style={{
              background: 'linear-gradient(135deg, #312E81 0%, #4F46E5 50%, #7C3AED 100%)',
              color: '#FFFFFF',
              padding: '20px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '24px' }}>🤖</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '800' }}>AI Kelishuv Maslahatchisi</h3>
                  <p style={{ margin: 0, fontSize: '11px', color: 'rgba(255,255,255,0.8)' }}>Tannarx va sof foyda tahlili (Deal Margin Guard)</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDealAdvisorModalOpen(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.15)',
                  border: 'none',
                  color: '#fff',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  cursor: 'pointer',
                  fontSize: '16px'
                }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px' }}>
              {dealAdvisorLoading ? (
                <div style={{ textAlign: 'center', padding: '40px 10px', color: '#6B7280' }}>
                  <div className="spinner" style={{ width: '40px', height: '40px', margin: '0 auto 16px' }}></div>
                  <div style={{ fontSize: '14px', fontWeight: '700' }}>Tannarx va zaxira partiyalari tahlil qilinmoqda...</div>
                </div>
              ) : dealAdvisorData ? (
                <div>
                  {/* Verdict Banner */}
                  <div style={{
                    background: dealAdvisorData.verdict_status === 'profitable'
                      ? '#ECFDF5'
                      : dealAdvisorData.verdict_status === 'warning'
                      ? '#FEFCE8'
                      : '#FEF2F2',
                    border: '1.5px solid ' + (dealAdvisorData.verdict_status === 'profitable'
                      ? '#10B981'
                      : dealAdvisorData.verdict_status === 'warning'
                      ? '#F59E0B'
                      : '#EF4444'),
                    padding: '16px',
                    borderRadius: '16px',
                    marginBottom: '20px',
                    textAlign: 'center'
                  }}>
                    <span style={{
                      display: 'inline-block',
                      fontSize: '14px',
                      fontWeight: '900',
                      color: dealAdvisorData.verdict_status === 'profitable'
                        ? '#065F46'
                        : dealAdvisorData.verdict_status === 'warning'
                        ? '#92400E'
                        : '#991B1B',
                      marginBottom: '6px'
                    }}>
                      {dealAdvisorData.verdict_badge}
                    </span>
                    <p style={{
                      margin: 0,
                      fontSize: '13px',
                      color: '#374151',
                      lineHeight: '1.5',
                      textAlign: 'left'
                    }}
                    dangerouslySetInnerHTML={{ __html: dealAdvisorData.ai_advice }}
                    />
                  </div>

                  {/* Financial Grid */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '12px',
                    marginBottom: '20px'
                  }}>
                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px', borderRadius: '14px' }}>
                      <span style={{ fontSize: '11px', color: '#64748B', fontWeight: '700', textTransform: 'uppercase' }}>Haqiqiy Tannarx</span>
                      <strong style={{ display: 'block', fontSize: '18px', color: '#1E293B', fontFamily: 'monospace', marginTop: '2px' }}>
                        {Math.round(dealAdvisorData.total_cost).toLocaleString('fr-FR')} so'm
                      </strong>
                    </div>

                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px', borderRadius: '14px' }}>
                      <span style={{ fontSize: '11px', color: '#64748B', fontWeight: '700', textTransform: 'uppercase' }}>Kutilayotgan Tushum</span>
                      <strong style={{ display: 'block', fontSize: '18px', color: '#4F46E5', fontFamily: 'monospace', marginTop: '2px' }}>
                        {Math.round(dealAdvisorData.total_revenue).toLocaleString('fr-FR')} so'm
                      </strong>
                    </div>

                    <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', padding: '12px', borderRadius: '14px' }}>
                      <span style={{ fontSize: '11px', color: '#15803D', fontWeight: '700', textTransform: 'uppercase' }}>Kutilayotgan Sof Foyda</span>
                      <strong style={{
                        display: 'block',
                        fontSize: '18px',
                        color: dealAdvisorData.net_profit >= 0 ? '#16A34A' : '#DC2626',
                        fontFamily: 'monospace',
                        marginTop: '2px'
                      }}>
                        {dealAdvisorData.net_profit >= 0 ? '+' : ''}{Math.round(dealAdvisorData.net_profit).toLocaleString('fr-FR')} so'm
                      </strong>
                    </div>

                    <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', padding: '12px', borderRadius: '14px' }}>
                      <span style={{ fontSize: '11px', color: '#15803D', fontWeight: '700', textTransform: 'uppercase' }}>Sof Marja (%)</span>
                      <strong style={{
                        display: 'block',
                        fontSize: '18px',
                        color: dealAdvisorData.overall_margin_pct >= 0 ? '#16A34A' : '#DC2626',
                        fontFamily: 'monospace',
                        marginTop: '2px'
                      }}>
                        {dealAdvisorData.overall_margin_pct >= 0 ? '+' : ''}{dealAdvisorData.overall_margin_pct}%
                      </strong>
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      type="button"
                      onClick={() => setDealAdvisorModalOpen(false)}
                      style={{
                        flex: 1,
                        padding: '13px',
                        background: '#F3F4F6',
                        border: '1.5px solid #E5E7EB',
                        borderRadius: '12px',
                        fontWeight: '700',
                        fontSize: '13px',
                        color: '#374151',
                        cursor: 'pointer'
                      }}
                    >
                      Boshqa narx qo'yish
                    </button>
                    <button
                      type="button"
                      onClick={() => setDealAdvisorModalOpen(false)}
                      style={{
                        flex: 1,
                        padding: '13px',
                        background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '12px',
                        fontWeight: '800',
                        fontSize: '13px',
                        cursor: 'pointer',
                        boxShadow: '0 4px 12px rgba(27,107,74,0.3)'
                      }}
                    >
                      ✅ Kelishuvni Tasdiqlash
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* ── AI FACE RECOGNITION MODAL ── */}
      {showFaceModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.8)',
          backdropFilter: 'blur(8px)',
          zIndex: 99999,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '16px'
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '24px',
            width: '100%',
            maxWidth: '520px',
            boxShadow: '0 24px 70px rgba(0,0,0,0.35)',
            overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.25)'
          }}>
            {/* Header */}
            <div style={{
              background: 'linear-gradient(135deg, #1B6B4A 0%, #0F3D2A 100%)',
              padding: '18px 22px',
              color: '#fff',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>🤖</div>
                <div style={{ textAlign: 'left' }}>
                  <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800' }}>AI Smart Kamera & Face ID</h4>
                  <div style={{ fontSize: '11px', opacity: 0.85 }}>Mijozni yuzidan tanish va ovozli salomlashish</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setShowAiSettings(!showAiSettings)}
                  title="AI Kamera va Ovoz Sozlamalari"
                  style={{
                    background: showAiSettings ? '#10B981' : 'rgba(255,255,255,0.2)',
                    border: '1px solid rgba(255,255,255,0.3)',
                    color: '#fff',
                    padding: '6px 11px',
                    borderRadius: '10px',
                    fontSize: '11.5px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    backdropFilter: 'blur(4px)',
                    transition: 'all 0.2s'
                  }}
                >
                  ⚙️ {showAiSettings ? 'Kamera' : 'Sozlamalar'}
                </button>
                <button
                  type="button"
                  onClick={switchCameraFacingMode}
                  title="Kamerani almashtirish (Oldi / Orqa kamera)"
                  style={{
                    background: 'rgba(255,255,255,0.2)',
                    border: '1px solid rgba(255,255,255,0.3)',
                    color: '#fff',
                    padding: '6px 11px',
                    borderRadius: '10px',
                    fontSize: '11.5px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    backdropFilter: 'blur(4px)'
                  }}
                >
                  🔄 {cameraFacingMode === 'user' ? 'Oldi' : 'Orqa'}
                </button>
                <button
                  onClick={() => { setShowFaceModal(false); stopFaceCamera(); setShowAiSettings(false); }}
                  style={{ background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff', width: '32px', height: '32px', borderRadius: '50%', fontSize: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  &times;
                </button>
              </div>
            </div>

            {/* ══════════ IF SETTINGS VIEW IS OPEN ══════════ */}
            {showAiSettings ? (
              <div style={{ padding: '20px', maxHeight: '440px', overflowY: 'auto', textAlign: 'left' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid #E2E8F0', paddingBottom: '8px' }}>
                  <h5 style={{ margin: 0, fontSize: '15px', fontWeight: '800', color: '#1E293B' }}>⚙️ AI Ovoz va Kamera Sozlamalari</h5>
                  <span style={{ fontSize: '11px', color: '#64748B' }}>Avtomatik saqlanadi</span>
                </div>

                {/* 1. Voice & Speech Settings */}
                <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '16px', padding: '14px', marginBottom: '14px' }}>
                  <div style={{ fontWeight: '800', fontSize: '13px', color: '#0F172A', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>🔊</span>
                    <span>Ovoz va Nutq Parametrlari</span>
                  </div>

                  {/* Volume */}
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                      <span>Ovoz Balandligi:</span>
                      <span style={{ color: '#1B6B4A', fontWeight: '800' }}>{Math.round(aiVoiceVolume * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={aiVoiceVolume}
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        setAiVoiceVolume(v);
                        saveAiSettingsToStorage({ vol: v });
                      }}
                      style={{ width: '100%', accentColor: '#1B6B4A' }}
                    />
                  </div>

                  {/* Rate / Speed */}
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                      <span>Gapirish Tezligi:</span>
                      <span style={{ color: '#1B6B4A', fontWeight: '800' }}>{aiVoiceRate.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range"
                      min="0.7"
                      max="1.3"
                      step="0.05"
                      value={aiVoiceRate}
                      onChange={(e) => {
                        const r = parseFloat(e.target.value);
                        setAiVoiceRate(r);
                        saveAiSettingsToStorage({ rate: r });
                      }}
                      style={{ width: '100%', accentColor: '#1B6B4A' }}
                    />
                  </div>

                  {/* Pitch / Tone */}
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                      <span>Ovoz Tembr / Baland-pastligi:</span>
                      <span style={{ color: '#1B6B4A', fontWeight: '800' }}>{aiVoicePitch.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.8"
                      max="1.3"
                      step="0.05"
                      value={aiVoicePitch}
                      onChange={(e) => {
                        const p = parseFloat(e.target.value);
                        setAiVoicePitch(p);
                        saveAiSettingsToStorage({ pitch: p });
                      }}
                      style={{ width: '100%', accentColor: '#1B6B4A' }}
                    />
                  </div>

                  {/* Voice Selector */}
                  {availableSynthVoices.length > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                        Diktorni Tanlash (Sintezator Ovozi):
                      </label>
                      <select
                        value={aiVoiceVoiceURI}
                        onChange={(e) => {
                          setAiVoiceVoiceURI(e.target.value);
                          saveAiSettingsToStorage({ voiceUri: e.target.value });
                        }}
                        style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1.5px solid #CBD5E1', fontSize: '12px', background: '#fff', color: '#1E293B' }}
                      >
                        <option value="">Avtomatik tanlash (Eng mos ovoz)</option>
                        {availableSynthVoices.map(v => (
                          <option key={v.voiceURI} value={v.voiceURI}>
                            {v.name} ({v.lang})
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Greeting Cooldown */}
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                      Bir xil odamga qayta salomlashish oralig'i (Tanaffus):
                    </label>
                    <select
                      value={aiVoiceCooldown}
                      onChange={(e) => {
                        const c = parseInt(e.target.value, 10);
                        setAiVoiceCooldown(c);
                        saveAiSettingsToStorage({ cooldown: c });
                      }}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1.5px solid #CBD5E1', fontSize: '12px', background: '#fff', color: '#1E293B' }}
                    >
                      <option value="10">10 soniya (Tezkor)</option>
                      <option value="20">20 soniya (Tavsiya etiladi)</option>
                      <option value="30">30 soniya (Vazmin)</option>
                      <option value="60">60 soniya (1 daqiqa)</option>
                    </select>
                  </div>

                  {/* Test speech button */}
                  <button
                    type="button"
                    onClick={testAiVoice}
                    style={{
                      background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                      color: '#fff',
                      border: 'none',
                      padding: '9px 16px',
                      borderRadius: '10px',
                      fontWeight: '800',
                      fontSize: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: '0 4px 12px rgba(37,99,235,0.25)'
                    }}
                  >
                    🔊 Sinov Ovozini Eshitish
                  </button>
                </div>

                {/* 2. Camera & Detection Settings */}
                <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '16px', padding: '14px', marginBottom: '14px' }}>
                  <div style={{ fontWeight: '800', fontSize: '13px', color: '#0F172A', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>📷</span>
                    <span>Kamera va Harakat Sezgirligi</span>
                  </div>

                  {/* Gaze filter */}
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                      Kameraga qarab turish talabi (Harakat filtri):
                    </label>
                    <select
                      value={aiGazeDuration}
                      onChange={(e) => {
                        const g = parseInt(e.target.value, 10);
                        setAiGazeDuration(g);
                        saveAiSettingsToStorage({ gaze: g });
                      }}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1.5px solid #CBD5E1', fontSize: '12px', background: '#fff', color: '#1E293B' }}
                    >
                      <option value="1">1.5 soniya (Tez sezish)</option>
                      <option value="2">2.5 soniya (O'rtacha - Tavsiya etiladi)</option>
                      <option value="3">3.5 soniya (Faqat to'xtab qaraganlarga)</option>
                    </select>
                  </div>
                </div>

                {/* Bottom Actions */}
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', paddingTop: '6px' }}>
                  <button
                    type="button"
                    onClick={resetAiSettingsToDefault}
                    style={{ background: '#F1F5F9', border: '1px solid #CBD5E1', color: '#475569', padding: '10px 14px', borderRadius: '10px', fontWeight: '700', fontSize: '12px', cursor: 'pointer' }}
                  >
                    🔄 Standartga qaytarish
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAiSettings(false)}
                    style={{ background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: '10px', fontWeight: '800', fontSize: '12px', cursor: 'pointer', boxShadow: '0 4px 12px rgba(27,107,74,0.25)' }}
                  >
                    ✅ Saqlash va Yopish
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Optional multi-camera selection dropdown if multiple cameras/USB webcams are found */}
                {availableCameras.length > 1 && (
                  <div style={{ padding: '8px 16px', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11.5px' }}>
                    <span style={{ fontWeight: '700', color: '#334155' }}>📷 Qurilma:</span>
                    <select
                      value={selectedCameraId}
                      onChange={(e) => selectSpecificCamera(e.target.value)}
                      style={{ flex: 1, padding: '5px 10px', borderRadius: '8px', border: '1px solid #CBD5E1', fontSize: '11.5px', background: '#fff', color: '#1E293B', outline: 'none' }}
                    >
                      <option value="">Avtomatik tanlash ({cameraFacingMode === 'user' ? 'Oldi' : 'Orqa'})</option>
                      {availableCameras.map((cam, idx) => (
                        <option key={cam.deviceId || idx} value={cam.deviceId}>
                          {cam.label || `Kamera #${idx + 1}`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Video Viewport */}
                <div style={{ position: 'relative', background: '#0A0F0D', height: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                  <video
                    ref={faceVideoRef}
                    autoPlay
                    playsInline
                    muted
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      transform: cameraFacingMode === 'user' ? 'scaleX(-1)' : 'none'
                    }}
                  />
                  <canvas
                    ref={faceCanvasRef}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      pointerEvents: 'none',
                      transform: cameraFacingMode === 'user' ? 'scaleX(-1)' : 'none'
                    }}
                  />

                  {/* Live 128-D Vector Stream Strip (HUD Top) */}
                  <div style={{
                    position: 'absolute',
                    top: '10px',
                    left: '12px',
                    right: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(0,0,0,0.78)',
                    backdropFilter: 'blur(8px)',
                    padding: '5px 10px',
                    borderRadius: '8px',
                    border: '1px solid rgba(56,189,248,0.3)'
                  }}>
                    <div style={{ fontFamily: 'monospace', fontSize: '10.5px', color: '#38BDF8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {live128Vector}
                    </div>
                    <span style={{ fontSize: '10px', fontWeight: '800', color: '#38BDF8', background: 'rgba(56,189,248,0.18)', padding: '1px 6px', borderRadius: '4px', marginLeft: '8px', flexShrink: 0 }}>
                      68 Mesh
                    </span>
                  </div>

                  {/* Target HUD Frame */}
                  <div style={{
                    position: 'absolute',
                    width: '170px',
                    height: '200px',
                    border: '2px dashed #81EFBB',
                    borderRadius: '18px',
                    boxShadow: '0 0 24px rgba(129,239,187,0.25)',
                    pointerEvents: 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    padding: '8px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#81EFBB', fontWeight: '800', fontSize: '14px' }}>⌜</span>
                      <span style={{ color: '#81EFBB', fontWeight: '800', fontSize: '14px' }}>⌝</span>
                    </div>
                    <div style={{ height: '2.5px', background: 'linear-gradient(90deg, transparent, #81EFBB, transparent)', boxShadow: '0 0 12px #81EFBB', animation: 'laserScan 2.2s infinite linear' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#81EFBB', fontWeight: '800', fontSize: '14px' }}>⌞</span>
                      <span style={{ color: '#81EFBB', fontWeight: '800', fontSize: '14px' }}>⌟</span>
                    </div>
                  </div>

                  {/* HUD Strip */}
                  <div style={{
                    position: 'absolute',
                    bottom: '12px',
                    left: '14px',
                    right: '14px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(0,0,0,0.78)',
                    backdropFilter: 'blur(8px)',
                    padding: '7px 14px',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.12)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isCameraActive ? '#10B981' : '#EF4444', animation: isCameraActive ? 'pulseDotLive 1.5s infinite' : 'none' }}></span>
                      <span style={{ fontSize: '12px', fontWeight: '700', color: '#FFFFFF' }}>{faceScanStatus}</span>
                    </div>
                    <span style={{ fontSize: '11px', fontWeight: '800', color: '#81EFBB', background: 'rgba(129,239,187,0.18)', padding: '2px 8px', borderRadius: '6px' }}>
                      {faceConfidence ? `${faceConfidence}% Moslik` : 'Auto 1.2s'}
                    </span>
                  </div>
                </div>

                {/* Content & Action */}
                <div style={{ padding: '16px 20px', maxHeight: '340px', overflowY: 'auto' }}>
                  {faceRecognizedCustomer && (
                    <div style={{
                      background: '#F0FDF4',
                      border: '1.5px solid #86EFAC',
                      borderRadius: '16px',
                      padding: '12px 14px',
                      marginBottom: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '10px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', textAlign: 'left' }}>
                        <img
                          src={faceRecognizedCustomer.image || '/static/images/default-avatar.png'}
                          alt=""
                          onError={(e) => { e.target.src = 'https://ui-avatars.com/api/?name=' + encodeURIComponent(faceRecognizedCustomer.name); }}
                          style={{ width: '46px', height: '46px', borderRadius: '12px', objectFit: 'cover', border: '2px solid #16A34A' }}
                        />
                        <div>
                          <div style={{ fontSize: '14.5px', fontWeight: '800', color: '#14532D' }}>
                            {faceRecognizedCustomer.name} (ID: {faceRecognizedCustomer.custom_id || faceRecognizedCustomer.id})
                          </div>
                          <div style={{ fontSize: '11.5px', color: '#166534', fontWeight: '600' }}>
                            Qarz: {Math.round(faceRecognizedCustomer.debt_amount || 0).toLocaleString()} so'm &bull; Bonus: {faceRecognizedCustomer.bonus_points || 0}
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          handleConfirmCustomer(faceRecognizedCustomer);
                          setShowFaceModal(false);
                          stopFaceCamera();
                        }}
                        style={{
                          background: 'linear-gradient(135deg, #16A34A 0%, #15803D 100%)',
                          color: '#fff',
                          border: 'none',
                          padding: '9px 16px',
                          borderRadius: '10px',
                          fontWeight: '800',
                          fontSize: '12.5px',
                          cursor: 'pointer',
                          boxShadow: '0 4px 12px rgba(22,163,74,0.25)'
                        }}
                      >
                        ⚡ Kassaga Ulash
                      </button>
                    </div>
                  )}

                  {/* Action Tabs: 1. Search existing | 2. Create new from snapshot */}
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                    <button
                      type="button"
                      onClick={() => setFaceModalTab('assign')}
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        borderRadius: '10px',
                        border: '1.5px solid ' + (faceModalTab === 'assign' ? '#81EFBB' : 'transparent'),
                        background: faceModalTab === 'assign' ? '#E8F5E9' : '#F1F5F9',
                        color: faceModalTab === 'assign' ? '#1B6B4A' : '#475569',
                        fontSize: '12px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      🔍 Mavjud Mijozga Biriktirish
                    </button>
                    <button
                      type="button"
                      onClick={() => setFaceModalTab('create')}
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        borderRadius: '10px',
                        border: '1.5px solid ' + (faceModalTab === 'create' ? '#81EFBB' : 'transparent'),
                        background: faceModalTab === 'create' ? '#E8F5E9' : '#F1F5F9',
                        color: faceModalTab === 'create' ? '#1B6B4A' : '#475569',
                        fontSize: '12px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      📸 Yangi Mijoz Yaratish
                    </button>
                  </div>

                  {faceAssignSuccessMsg && (
                    <div style={{ background: '#ECFDF5', color: '#065F46', padding: '8px 12px', borderRadius: '10px', fontSize: '12px', fontWeight: '700', marginBottom: '10px' }}>
                      {faceAssignSuccessMsg}
                    </div>
                  )}

                  {/* TAB 1: Live Customer Search Dropdown */}
                  {faceModalTab === 'assign' && (
                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '16px', padding: '12px 14px' }}>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#334155', marginBottom: '6px' }}>
                        🔍 Mijozni qidirish (Ismi yoki Telefon raqami):
                      </label>
                      <input
                        type="text"
                        placeholder="Ism yoki telefon yozing..."
                        value={faceCustSearchText}
                        onChange={(e) => setFaceCustSearchText(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', outline: 'none', background: '#FFFFFF' }}
                      />

                      {faceCustSearchText && (
                        <div style={{ maxHeight: '140px', overflowY: 'auto', background: '#FFFFFF', border: '1px solid #CBD5E1', borderRadius: '10px', marginTop: '6px' }}>
                          {(Array.isArray(cachedCustomers) ? cachedCustomers : [])
                            .filter(c => {
                              const q = faceCustSearchText.toLowerCase();
                              return (c.name || '').toLowerCase().includes(q) || (c.phone || '').includes(q);
                            })
                            .slice(0, 6)
                            .map(c => (
                              <div
                                key={c.id}
                                onClick={() => {
                                  setFaceAssignCustId(c.id);
                                  setFaceSelectedCust(c);
                                  setFaceCustSearchText(c.name || `${c.first_name || ''} ${c.last_name || ''}`);
                                }}
                                style={{ padding: '8px 12px', borderBottom: '1px solid #F1F5F9', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                              >
                                <div>
                                  <div style={{ fontWeight: '700', fontSize: '12.5px', color: '#1E293B' }}>{c.name || c.first_name}</div>
                                  <div style={{ fontSize: '11px', color: '#64748B' }}>{c.phone} &bull; Qarz: {Math.round(c.debt_amount || 0).toLocaleString()} so'm</div>
                                </div>
                                <span style={{ fontSize: '11px', fontWeight: '800', color: '#2563EB', background: '#EFF6FF', padding: '2px 8px', borderRadius: '6px' }}>Tanlash</span>
                              </div>
                            ))}
                        </div>
                      )}

                      {faceSelectedCust && (
                        <div style={{ marginTop: '10px', padding: '8px 12px', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontSize: '12.5px', fontWeight: '800', color: '#1E40AF' }}>Tanlandi: {faceSelectedCust.name}</div>
                            <div style={{ fontSize: '11px', color: '#3B82F6' }}>{faceSelectedCust.phone}</div>
                          </div>
                          <button
                            type="button"
                            disabled={faceAssignSaving}
                            onClick={handleSaveFaceToCustomer}
                            style={{ background: '#2563EB', color: '#fff', border: 'none', padding: '7px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: '700', cursor: 'pointer' }}
                          >
                            💾 Face ID Saqlash
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 2: Create New Customer with Face Snapshot */}
                  {faceModalTab === 'create' && (
                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '16px', padding: '12px 14px' }}>
                      <div style={{ fontSize: '12px', fontWeight: '700', color: '#1E293B', marginBottom: '8px' }}>
                        📸 Kameradagi yuzdan to'g'ridan-to'g'ri yangi mijoz yaratish:
                      </div>
                      
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '11px', fontWeight: '700', color: '#475569', marginBottom: '3px' }}>Ism va Familiya *</label>
                          <input
                            type="text"
                            placeholder="Masalan: Sardor Aliyev"
                            value={aiNewCustName}
                            onChange={(e) => setAiNewCustName(e.target.value)}
                            style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1.5px solid #CBD5E1', fontSize: '12.5px' }}
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: '11px', fontWeight: '700', color: '#475569', marginBottom: '3px' }}>Telefon raqami *</label>
                          <input
                            type="text"
                            placeholder="+998 90 123 45 67"
                            value={aiNewCustPhone}
                            onChange={(e) => setAiNewCustPhone(e.target.value)}
                            style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1.5px solid #CBD5E1', fontSize: '12.5px' }}
                          />
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>
                          128-D Yuz vektori va surat avtomatik biriktiriladi
                        </div>
                        <button
                          type="button"
                          disabled={faceAssignSaving}
                          onClick={handleCreateNewCustomerWithFace}
                          style={{ background: 'linear-gradient(135deg, #1B6B4A 0%, #2D9B6E 100%)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '10px', fontSize: '12px', fontWeight: '800', cursor: 'pointer', boxShadow: '0 4px 12px rgba(27,107,74,0.25)' }}
                        >
                          ✨ Yaratish & Face ID Saqlash
                        </button>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button
                        type="button"
                        onClick={toggleFaceCamera}
                        style={{
                          background: isCameraActive ? '#F1F5F9' : '#1B6B4A',
                          color: isCameraActive ? '#1E293B' : '#fff',
                          border: '1px solid #CBD5E1',
                          padding: '8px 14px',
                          borderRadius: '10px',
                          fontSize: '12px',
                          fontWeight: '700',
                          cursor: 'pointer'
                        }}
                      >
                        {isCameraActive ? "🛑 O'chirish" : "▶️ Yoqish"}
                      </button>
                      <button
                        type="button"
                        onClick={() => scanFaceSnapshot(false)}
                        style={{
                          background: '#1B6B4A',
                          color: '#fff',
                          border: 'none',
                          padding: '8px 16px',
                          borderRadius: '10px',
                          fontSize: '12px',
                          fontWeight: '700',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          boxShadow: '0 4px 12px rgba(27,107,74,0.2)'
                        }}
                      >
                        📸 Hozir Skanerlash
                      </button>
                    </div>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: '700', color: '#334155', margin: 0 }}>
                      <input
                        type="checkbox"
                        checked={isFaceVoiceEnabled}
                        onChange={(e) => setIsFaceVoiceEnabled(e.target.checked)}
                        style={{ accentColor: '#1B6B4A', width: '16px', height: '16px' }}
                      />
                      <span>🔊 Ovozli Salom</span>
                    </label>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
