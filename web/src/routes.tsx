import { createBrowserRouter } from 'react-router-dom'
import MapPage from './pages/MapPage'
import DistrictPage from './pages/DistrictPage'
import EarlyEstimatePage from './pages/EarlyEstimatePage'
import ScenarioPage from './pages/ScenarioPage'
import MethodologyPage from './pages/MethodologyPage'
import DataPage from './pages/DataPage'
import AboutPage from './pages/AboutPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MapPage />,
  },
  {
    path: '/districts/:code',
    element: <DistrictPage />,
  },
  {
    path: '/early-estimate',
    element: <EarlyEstimatePage />,
  },
  {
    path: '/scenario',
    element: <ScenarioPage />,
  },
  {
    path: '/methodology',
    element: <MethodologyPage />,
  },
  {
    path: '/data',
    element: <DataPage />,
  },
  {
    path: '/about',
    element: <AboutPage />,
  },
])
