import { useState, useEffect } from 'react'
import { Layout } from './components/Layout/Layout'
import { BackendBanner } from './components/BackendBanner'
import { StatusCard } from './components/StatusCard'
import { RecentJobs } from './components/RecentJobs'
import { ChatDock } from './components/ChatDock'
import { StatusDrawer } from './components/StatusDrawer'
import { fetchRoots, fetchJobs } from './lib/api'

function App() {
  const [jobs, setJobs] = useState<any[]>([])
  const [roots, setRoots] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const refreshStatus = async () => {
    setLoading(true)
    try {
      const [jobsData, rootsData] = await Promise.all([
        fetchJobs({ limit: 8, resolve_urls: false }),
        fetchRoots()
      ])
      setJobs(jobsData)
      setRoots(rootsData)
    } catch (error) {
      console.error('Failed to refresh status:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshStatus()
  }, [])

  // actions removed (ActionCards no longer rendered)

  return (
    <Layout>
      <BackendBanner />
      
      <div className="container mx-auto px-4 py-8">
        <div className="grid gap-6">
          <StatusCard 
            jobs={jobs} 
            roots={roots} 
            loading={loading}
            onOpenDrawer={() => setDrawerOpen(true)}
          />
          
          
          <RecentJobs jobs={jobs} loading={loading} />
        </div>
      </div>

      <ChatDock />
      
      <StatusDrawer 
        open={drawerOpen} 
        onClose={() => setDrawerOpen(false)}
        onRefresh={refreshStatus}
      />
    </Layout>
  )
}

export default App