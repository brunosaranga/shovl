import React from 'react'
import { useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'

export default function Settings() {
    const navigate = useNavigate()

    return (
        <PageShell centerElement={<PageTitle>settings</PageTitle>}>
            <div className="settings-container">
                
                {/* Account Section */}
                <section className="settings-section-card">
                    <div className="settings-section-header">Account</div>
                    <div className="settings-section-body">
                        <div className="settings-row">
                            <span className="settings-label">Username</span>
                            <span className="settings-value">userNameuser</span>
                            <button className="btn-neon-sm">Edit</button>
                        </div>
                        <div className="settings-row">
                            <span className="settings-label">Email</span>
                            <span className="settings-value">user@email.com</span>
                            <button className="btn-neon-sm">Edit</button>
                        </div>
                        <div className="settings-row">
                            <span className="settings-label">Password</span>
                            <span className="settings-value">********</span>
                            <button className="btn-neon-sm">Edit</button>
                        </div>
                    </div>
                </section>

                {/* Verified Domains Section */}
                <section className="settings-section-card">
                    <div className="settings-section-header">Verified Domains</div>
                    <div className="settings-section-body">
                        <div className="settings-row">
                            <span className="settings-label">api.example.com</span>
                            <span className="badge-verified">✓</span>
                            <button className="btn-danger-sm">Remove</button>
                        </div>
                        <div className="settings-row">
                            <span className="settings-label">api.startup.io</span>
                            <span className="badge-verified">✓</span>
                            <button className="btn-danger-sm">Remove</button>
                        </div>
                        <button className="btn-neon-sm btn-neon-action">+ Add domain</button>
                    </div>
                </section>

                {/* Subscription Section */}
                <section className="settings-section-card">
                    <div className="settings-section-header">Subscription</div>
                    <div className="settings-section-body">
                        <div className="settings-row">
                            <span className="settings-label">Plan:</span>
                            <span className="settings-value">Free</span>
                            <div></div> {/* Empty column for alignment matching grid */}
                        </div>
                        <div className="settings-row">
                            <span className="settings-label">Scans</span>
                            <span className="settings-value">0/6 this month</span>
                            <div></div>
                        </div>
                        <button className="btn-neon-sm btn-neon-action">Upgrade to Pro</button>
                    </div>
                </section>

                {/* API Keys Section */}
                <section className="settings-section-card">
                    <div className="settings-section-header">API Keys</div>
                    <div className="settings-section-body">
                        <div className="settings-row">
                            <span className="settings-label">sk_shovel_********</span>
                            <span className="settings-value">Created Jun 14 2026</span>
                            <button className="btn-neon-sm">Reveal</button>
                        </div>
                        <button className="btn-neon-sm btn-neon-action">+ Generate new key</button>
                    </div>
                </section>

                {/* Danger Zone Section */}
                <section className="settings-section-card">
                    <div className="settings-section-header">Danger Zone</div>
                    <div className="settings-section-body">
                        <div className="danger-zone-text">Permanently delete your account</div>
                        <button className="btn-danger-sm btn-neon-action">Delete account</button>
                    </div>
                </section>

            </div>
        </PageShell>
    )
}