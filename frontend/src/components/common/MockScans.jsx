import React from 'react'

const scans = [
    {
        id: 'scan-01',
        target: 'https://api.example.com',
        status: 'scanning',
        progress: 60,
        risk: 'CRITICAL',
        date: 'Jun 14 2026',
        logs: [
            '>> [14:48:01] initializing shovl engine...',
            '>> [14:48:03] establishing secure tunnel...',
            '>> [14:48:05] analyzing endpoint routing tables...',
            '>> [14:48:12] probing https://api.example.com for auth bypass...'
        ]
    },
    {
        id: 'scan-02',
        target: 'https://api.secure-bank.com',
        status: 'completed',
        progress: 100,
        risk: 'HIGH',
        date: 'Jun 14 2026'
    },
    {
        id: 'scan-03',
        target: 'https://internal.dev.system',
        status: 'completed',
        progress: 100,
        risk: 'MED',
        date: 'Jun 14 2026'
    }
]

export default scans;