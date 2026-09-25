import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopHeader } from './TopHeader'

export function ApplicationShell({ children }: { children?: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#F7F7F5] text-[#17181C]">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto">
          {children || <Outlet />}
        </main>
      </div>
    </div>
  )
}
