import { useEffect, useState } from 'react'
import { getHashPath } from '../routes/router'

export function useHashPath() {
  const [path, setPath] = useState(getHashPath())

  useEffect(() => {
    function handleHashChange() {
      setPath(getHashPath())
    }

    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  return path
}
