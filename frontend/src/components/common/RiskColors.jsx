import React from 'react'

const getRiskColor = (risk) => {
    switch (risk) {
        case 'CRITICAL': return '#ff4d4f'
        case 'HIGH': return '#ff9f43'
        case 'MED': return '#ffdd59'
        default: return '#111'
    }
}

export default getRiskColor;