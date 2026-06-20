import React from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PrimaryButton } from '../layout/Buttons'
import scans from '../common/MockScans'

export default function ScanStats() {
    const navigate = useNavigate()



    return (
        <div className='highlevel-stats-container'>
            {/* Executive View / High-Level Stats & CTA */}
            <div className='highlevel-stats'>
                <div 
                className='active-scans-container'>

                    <div 
                    className='active-scans'>
                        <span className='active-scans-title'>Active Scans</span>
                        
                        <span className='active-scans-no'>
                            {scans.filter(s => s.status === 'scanning').length}
                        </span>
                    </div>
                    
                    {/* Delimiter line */}
                    <div className='active-scan-delimiter-line'/>


                    <div className='threat-alerts'>
                        <span className='threat-label'>Threat Alerts</span>

                        <div 
                        className='threat-values'>

                            <span className='threat-value-content' style={{ background: '#ff4d4f', }}>CRIT: 1</span>

                            <span className='threat-value-content' style={{ background: '#ff9f43', }}>HIGH: 1</span>

                        </div>
                    </div>
                </div>

                <PrimaryButton onClick={() => navigate('/')}>
                    + new scan
                </PrimaryButton>
            </div>
        </div>
    )
}