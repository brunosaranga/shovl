// import { useEffect, useRef } from 'react'

// export default function GroundCanvas({ height = 260 }) {
//     const canvasRef = useRef(null)

//     useEffect(() => {
//         const canvas = canvasRef.current
//         const ctx = canvas.getContext('2d')
//         let t = 0
//         let animId

//         const resize = () => {
//             canvas.width = canvas.offsetWidth
//             canvas.height = canvas.offsetHeight
//         }
//         resize()
//         window.addEventListener('resize', resize)

//         // drawing logic

//         const loop = () => {
//             t += 1
//             draw(ctx, canvas, t)
//             animId = requestAnimationFrame(loop)
//         }
//         loop()

//         return () => {
//             cancelAnimationFrame(animId)
//             window.removeEventListener('resize', resize)
//         }
//     }, [])

//     return (
//         <canvas
//             ref={canvasRef}
//             style={{
//                 display: 'block',
//                 width: '100%',
//                 height: `${height}px`,
//                 position: 'absolute',
//                 bottom: 0,
//                 left: 0,
//             }}
//         />
//     )
// }




// frontend/src/components/layout/GroundCanvas.jsx
import groundImage from '../../assets/ground.png'

export default function GroundCanvas() {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: '100%',
        height: '300px',
        backgroundImage: `url(${groundImage})`,
        backgroundSize: 'cover',
        backgroundPosition: 'bottom center',
        backgroundRepeat: 'no-repeat',
        pointerEvents: 'none', // Allows clicks through the background
        zIndex: 1,
      }}
    />
  )
}