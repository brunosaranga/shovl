import React from 'react';

// Import your raw Figma exports
import verboseOn from '../../assets/verboseKnobOn.svg';
import verboseOff from '../../assets/verboseKnobOff.svg';
import reportOn from '../../assets/genReportKnobOn.svg';
import reportOff from '../../assets/genReportKnobOff.svg';
import fixOn from '../../assets/suggestFixKnobOn.svg';
import fixOff from '../../assets/suggestFixKnobOff.svg';

const KNOB_ASSETS = {
  'verbose': { 
    on: verboseOn, 
    off: verboseOff,
    onAngle: '0deg',      // Exact rotation when active
    offAngle: '-50deg'    // Your exact -50% layout alignment from Figma
  },
  'generate report': { 
    on: reportOn, 
    off: reportOff,
    onAngle: '0deg', 
    offAngle: '-45deg' 
  },
  'suggest fix': { 
    on: fixOn, 
    off: fixOff,
    onAngle: '15deg',     // Tweak individual knobs if you want a custom click throw!
    offAngle: '-35deg' 
  }
};

export default function KnobToggle({ label, active, onChange, offsetY = 0 }) {
  const config = KNOB_ASSETS[label] || KNOB_ASSETS['verbose'];
  
  // 1. Swap the vector graphic asset
  const currentAsset = active ? config.on : config.off;
  
  // 2. Select the specific CSS degree rule for this state
  const currentRotation = active ? config.onAngle : config.offAngle;

  return (
    <div
      className='knob-toggle-container'
      onClick={() => onChange(!active)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        cursor: 'pointer',
        userSelect: 'none',
        width: '140px',
        transform: `translateY(${offsetY}px)`,
        // transition: 'transform 0.2s ease-in-out'
      }}
    >
      {/* The Figma Vector Engine + CSS Mechanical Snap */}
      <img 
        src={currentAsset} 
        alt={label}
        style={{
          width: '124px',
          height: '124px',
          // adds a shadow
          // filter: 'drop-shadow(3px 3px 0px #111111)',
          
          // 3. Apply the rotation angle dynamic state
          transform: `rotate(${currentRotation})`,
          transformOrigin: 'center center', // Keeps rotation perfectly anchored in the square frame
          
          // A heavy, snappy spring curve to make the knob feel premium and tactile
          // transition: 'transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275), filter 0.1s ease'
        }}
        // Click feel: slightly shrinks the asset on click pressure
        onMouseDown={(e) => e.currentTarget.style.transform = `rotate(${currentRotation}) scale(0.92)`}
        onMouseUp={(e) => e.currentTarget.style.transform = `rotate(${currentRotation}) scale(1)`}
      />

      <span 
        style={{
          marginTop: '4px',
          display: 'block',
          fontFamily: 'var(--font-display)',
          fontWeight: '300',
          fontSize: '22px',
          color: 'var(--color-text)',
          textAlign: 'center',
          textTransform: 'lowercase',
          whiteSpace: 'wrap'
        }}
      >
        {label}
      </span>
    </div>
  );
}