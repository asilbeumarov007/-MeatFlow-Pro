import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("POS Terminal UI Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: '#F5F1EB',
          fontFamily: 'Inter, sans-serif',
          padding: '20px',
          textAlign: 'center'
        }}>
          <div style={{
            background: '#fff',
            border: '1.5px solid rgba(0,0,0,0.08)',
            borderRadius: '24px',
            padding: '36px 28px',
            maxWidth: '420px',
            boxShadow: '0 10px 40px rgba(0,0,0,0.08)'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>🥩</div>
            <h2 style={{ fontSize: '20px', fontWeight: '800', color: '#1A1A2E', marginBottom: '8px' }}>
              MeatFlow POS Terminal
            </h2>
            <p style={{ fontSize: '13px', color: '#6B7280', marginBottom: '12px', lineHeight: '1.5' }}>
              Terminal interfeysida xatolik yuz berdi. Iltimos, quyidagi tugmani bosib terminalni qayta ishga tushiring:
            </p>
            {this.state.error && (
              <div style={{
                background: '#FEF2F2',
                border: '1px solid #FECACA',
                borderRadius: '10px',
                padding: '10px',
                fontSize: '11px',
                color: '#DC3545',
                textAlign: 'left',
                marginBottom: '16px',
                fontFamily: 'monospace',
                maxHeight: '120px',
                overflowY: 'auto'
              }}>
                {this.state.error.toString()}
              </div>
            )}
            <button
              onClick={() => {
                localStorage.removeItem('offline_sales');
                window.location.reload();
              }}
              style={{
                width: '100%',
                padding: '14px',
                background: 'linear-gradient(135deg, #1B6B4A, #2D9B6E)',
                color: '#fff',
                border: 'none',
                borderRadius: '14px',
                fontSize: '15px',
                fontWeight: 'bold',
                cursor: 'pointer',
                marginBottom: '10px'
              }}
            >
              🔄 Qayta yuklash (Reload)
            </button>
            <button
              onClick={() => { window.location.href = '/pos/daily-report/'; }}
              style={{
                width: '100%',
                padding: '12px',
                background: 'transparent',
                color: '#6B7280',
                border: '1px solid rgba(0,0,0,0.1)',
                borderRadius: '14px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              📊 Kunlik hisobotga o'tish
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
