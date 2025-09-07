import { useState, useEffect } from 'react'
import { Layout } from './components/layout/Layout'
import { BackendBanner } from './components/BackendBanner'
import { StatusCard } from './components/StatusCard'
import { RecentJobs } from './components/RecentJobs'
import { ActionCards } from './components/ActionCards'
import { ChatDock } from './components/ChatDock'
import { StatusDrawer } from './components/StatusDrawer'
import { pingAPI, fetchRoots, fetchJobs, postEdit, postPoses, postAnimate } from './lib/api'

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

  const actions = [
    {
      key: 'ping',
      label: 'Ping Backend',
      onClick: async () => {
        const result = await pingAPI()
        console.log('Ping result:', result)
      }
    },
    {
      key: 'roots',
      label: 'Check Roots',
      onClick: async () => {
        const result = await fetchRoots()
        setRoots(result)
        console.log('Roots:', result)
      }
    },
    {
      key: 'status',
      label: 'Refresh Status',
      onClick: refreshStatus
    },
    {
      key: 'poses',
      label: 'Make Poses',
      onClick: async () => {
        const result = await postPoses({
          image_path: 'assets/inputs/char.png',
          poses: [{ name: 'idle' }, { name: 'walk' }],
          fps: 8,
          sheet_cols: 4
        })
        console.log('Poses result:', result)
        await refreshStatus()
      }
    },
    {
      key: 'edit',
      label: 'Nano Edit',
      onClick: async () => {
        const result = await postEdit({
          items: [{
            image_path: 'assets/inputs/char.png',
            instruction: 'make the cloak blue and add sparkles'
          }]
        })
        console.log('Edit result:', result)
        await refreshStatus()
      }
    },
    {
      key: 'animate',
      label: 'Animate',
      onClick: async () => {
        const result = await postAnimate({
          items: [{
            frames: ['frame1.png', 'frame2.png', 'frame3.png'],
            fps: 8,
            sheet_cols: 4,
            basename: 'test_anim'
          }]
        })
        console.log('Animate result:', result)
        await refreshStatus()
      }
    }
  ]

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
          
          <ActionCards items={actions} />
          
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