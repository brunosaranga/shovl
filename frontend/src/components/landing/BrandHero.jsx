import React from 'react'
import shovlGraphic from '../../assets/ShovelGraphic.svg'

// Background shovel graphic + "shovl" wordmark, layered together since
// they're positioned as one visual unit behind the action button.
export default function BrandHero() {
    return (
        <>
            <div className='shovel-graphic-container'>
                <img className='shovel-graphic' src={shovlGraphic} alt="" />
            </div>

            <div className='brand-wordmark-container'>
                <h1 className='brand-wordmark'>shovl</h1>
            </div>
        </>
    )
}