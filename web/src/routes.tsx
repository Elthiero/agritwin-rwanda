import { createBrowserRouter } from 'react-router-dom'
import MapPage from './pages/MapPage'
import DistrictPage from './pages/DistrictPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MapPage />,
  },
  {
    path: '/districts/:code',
    element: <DistrictPage />,
  },
])
