import React from 'react';

export const ComingSoonPage: React.FC = () => {
  return (
    <div style={{
      width: '100%',
      height: '80vh',
      backgroundImage: 'url(/BG-09.jpg)',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
      backgroundAttachment: 'fixed',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif',
      WebkitFontSmoothing: 'antialiased',
      MozOsxFontSmoothing: 'grayscale',
    }}>
      <div style={{
        textAlign: 'center',
        background: 'rgba(255, 255, 255, 0.95)',
        padding: '60px 40px',
        borderRadius: '12px',
        boxShadow: '0 10px 40px rgba(0, 0, 0, 0.2)',
        maxWidth: '600px',
        backdropFilter: 'blur(10px)',
      }}>
        <h1 style={{
          fontSize: '3.5rem',
          color: '#333',
          marginBottom: '20px',
          fontWeight: 700,
          letterSpacing: '-1px',
        }}>
          Coming Soon
          <span style={{
            display: 'inline-block',
            marginLeft: '8px',
            fontSize: '1.2rem',
          }}>
            <Dots />
          </span>
        </h1>
        <p style={{
          fontSize: '1.2rem',
          color: '#666',
          marginBottom: '30px',
          lineHeight: 1.6,
        }}>
          We're working on something amazing. Stay tuned!
        </p>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% {
            opacity: 0.5;
            transform: translateY(0);
          }
          40% {
            opacity: 1;
            transform: translateY(-10px);
          }
        }

        .dot {
          animation: bounce 1.4s infinite;
          margin: 0 4px;
          display: inline-block;
          color: #333;
        }

        .dot:nth-child(1) {
          animation-delay: 0s;
        }

        .dot:nth-child(2) {
          animation-delay: 0.2s;
        }

        .dot:nth-child(3) {
          animation-delay: 0.4s;
        }

        @media (max-width: 768px) {
          .coming-soon-container {
            padding: 40px 20px;
          }

          .coming-soon-title {
            font-size: 2.5rem;
          }

          .coming-soon-text {
            font-size: 1rem;
          }
        }

        @media (max-width: 480px) {
          .coming-soon-container {
            padding: 30px 15px;
          }

          .coming-soon-title {
            font-size: 1.8rem;
          }

          .coming-soon-text {
            font-size: 0.9rem;
          }
        }
      `}</style>
    </div>
  );
};

const Dots: React.FC = () => (
  <>
    <span className="dot">.</span>
    <span className="dot">.</span>
    <span className="dot">.</span>
  </>
);
